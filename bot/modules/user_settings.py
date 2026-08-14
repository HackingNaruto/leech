#!/usr/bin/env python3
"""
KPSML-X User Settings Module
Command: /usetting
Allows per-user toggle and configuration of media processing features:
- Sample Video (ON/OFF + duration)
- Convert Video (ON/OFF + format)
- Intro Subtitle (ON/OFF + text + duration)
- Smart Audio Tag (ON/OFF + tag text)
- Auto Merge Zip (ON/OFF)
"""

from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, regex
from asyncio import sleep

from bot import bot, user_data, DATABASE_URL, LOGGER
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.db_handler import DbManger

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

KEY_KEEP_LOCAL       = "us_keep_local"
KEY_SAMPLE_VIDEO     = "sample_video"
KEY_SAMPLE_DURATION  = "sample_duration"
KEY_CONVERT_VIDEO    = "convert_video"
KEY_CONVERT_FORMAT   = "convert_format"
KEY_INTRO_SUB        = "intro_sub"
KEY_INTRO_TEXT       = "intro_text"
KEY_INTRO_DURATION   = "intro_duration"
KEY_AUDIO_TAG        = "audio_tag"
KEY_AUDIO_TAG_TEXT   = "audio_tag_text"
KEY_AUTO_MERGE       = "auto_merge_zip"

_awaiting_text: dict[int, str] = {}


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _get_user_setting(user_id: int, key: str, default=None):
    return user_data.get(user_id, {}).get(key, default)


async def _set_user_setting(user_id: int, key: str, value):
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][key] = value
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)


def _bool_emoji(val: bool) -> str:
    return "✅" if val else "❌"


def _build_main_menu(user_id: int) -> tuple[str, object]:
    kl = _get_user_setting(user_id, KEY_KEEP_LOCAL, False)
    sv = _get_user_setting(user_id, KEY_SAMPLE_VIDEO, False)
    sd = _get_user_setting(user_id, KEY_SAMPLE_DURATION, 60)
    cv = _get_user_setting(user_id, KEY_CONVERT_VIDEO, False)
    cf = _get_user_setting(user_id, KEY_CONVERT_FORMAT, "mkv")
    isub = _get_user_setting(user_id, KEY_INTRO_SUB, False)
    it = _get_user_setting(user_id, KEY_INTRO_TEXT, "")
    idur = _get_user_setting(user_id, KEY_INTRO_DURATION, 30)
    at = _get_user_setting(user_id, KEY_AUDIO_TAG, False)
    att = _get_user_setting(user_id, KEY_AUDIO_TAG_TEXT, "")
    am = _get_user_setting(user_id, KEY_AUTO_MERGE, False)

    text = (
        "<b>🎛️ Your Personal Settings</b>\n\n"
        f"<b>💾 Storage Options</b>\n"
        f"  └ Keep Local (No Upload): {_bool_emoji(kl)}\n\n"
        f"<b>🎬 Video Engine</b>\n"
        f"  ├ Sample Video   : {_bool_emoji(sv)}\n"
        f"  ├ Sample Duration: {sd}s\n"
        f"  ├ Convert Video  : {_bool_emoji(cv)}\n"
        f"  └ Convert Format : {cf.upper()}\n\n"
        f"<b>📝 Intro Subtitle</b>\n"
        f"  ├ IntroSub       : {_bool_emoji(isub)}\n"
        f"  ├ Intro Text     : {it or '(not set)'}\n"
        f"  └ Duration       : {idur}s\n\n"
        f"<b>🏷️ Audio Tag</b>\n"
        f"  ├ Audio Tag      : {_bool_emoji(at)}\n"
        f"  └ Tag Text       : {att or '(not set)'}\n\n"
        f"<b>📦 Auto Merge</b>\n"
        f"  └ Zip Auto Merge : {_bool_emoji(am)}\n"
    )

    btn = ButtonMaker()

    btn.ibutton(f"💾 Keep Local {_bool_emoji(kl)}", f"us_toggle_{KEY_KEEP_LOCAL}")
    btn.ibutton(f"🎬 Sample Video {_bool_emoji(sv)}", f"us_toggle_{KEY_SAMPLE_VIDEO}")
    btn.ibutton(f"⏱ Duration: {sd}s", f"us_menu_sample_dur")
    btn.ibutton(f"🔄 Convert Video {_bool_emoji(cv)}", f"us_toggle_{KEY_CONVERT_VIDEO}")
    btn.ibutton(f"📦 Format: {cf.upper()}", f"us_menu_convert_fmt")

    btn.ibutton(f"📝 IntroSub {_bool_emoji(isub)}", f"us_toggle_{KEY_INTRO_SUB}")
    btn.ibutton("✏️ Set Intro Text", f"us_set_text_{KEY_INTRO_TEXT}")
    btn.ibutton(f"⏱ IntroSub Dur: {idur}s", f"us_menu_intro_dur")

    btn.ibutton(f"🏷️ Audio Tag {_bool_emoji(at)}", f"us_toggle_{KEY_AUDIO_TAG}")
    btn.ibutton("✏️ Set Tag Text", f"us_set_text_{KEY_AUDIO_TAG_TEXT}")

    btn.ibutton(f"📦 Auto Merge Zip {_bool_emoji(am)}", f"us_toggle_{KEY_AUTO_MERGE}")

    btn.ibutton("❌ Close", "us_close")

    return text, btn.build_menu(2)


def _build_sub_menu(menu_type: str, current_value) -> tuple[str, object]:
    btn = ButtonMaker()
    if menu_type == "sample_dur":
        title = "⏱ Select Sample Video Duration"
        for dur in [15, 30, 60]:
            mark = "✅ " if current_value == dur else ""
            btn.ibutton(f"{mark}{dur}s", f"us_set_{KEY_SAMPLE_DURATION}_{dur}")
    elif menu_type == "intro_dur":
        title = "⏱ Select IntroSub Duration"
        for dur in [15, 30, 60]:
            mark = "✅ " if current_value == dur else ""
            btn.ibutton(f"{mark}{dur}s", f"us_set_{KEY_INTRO_DURATION}_{dur}")
    elif menu_type == "convert_fmt":
        title = "📦 Select Output Format"
        for fmt in ["mkv", "mp4", "avi"]:
            mark = "✅ " if current_value == fmt else ""
            btn.ibutton(f"{mark}{fmt.upper()}", f"us_set_{KEY_CONVERT_FORMAT}_{fmt}")
    else:
        title = "Unknown menu"

    btn.ibutton("⬅️ Back", "us_back")
    return f"<b>{title}</b>", btn.build_menu(3)


# ─────────────────────────────────────────────
#  COMMAND HANDLER
# ─────────────────────────────────────────────

async def user_settings_cmd(client, message):
    user_id = message.from_user.id
    text, keyboard = _build_main_menu(user_id)
    await sendMessage(message, text, keyboard)


# ─────────────────────────────────────────────
#  CALLBACK HANDLER
# ─────────────────────────────────────────────

async def user_settings_cb(client, callback_query):
    query = callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if data.startswith("us_toggle_"):
        key = data.replace("us_toggle_", "")
        current = _get_user_setting(user_id, key, False)
        await _set_user_setting(user_id, key, not current)
        text, keyboard = _build_main_menu(user_id)
        await editMessage(query.message, text, keyboard)

    elif data.startswith("us_menu_"):
        menu_type = data.replace("us_menu_", "")
        if menu_type == "sample_dur":
            cur = _get_user_setting(user_id, KEY_SAMPLE_DURATION, 60)
        elif menu_type == "intro_dur":
            cur = _get_user_setting(user_id, KEY_INTRO_DURATION, 30)
        elif menu_type == "convert_fmt":
            cur = _get_user_setting(user_id, KEY_CONVERT_FORMAT, "mkv")
        else:
            cur = None
        text, keyboard = _build_sub_menu(menu_type, cur)
        await editMessage(query.message, text, keyboard)

    elif data.startswith("us_set_"):
        inner = data[len("us_set_"):]
        matched_key = None
        matched_val = None
        for k in [KEY_SAMPLE_DURATION, KEY_INTRO_DURATION, KEY_CONVERT_FORMAT]:
            if inner.startswith(k + "_"):
                matched_key = k
                matched_val = inner[len(k) + 1:]
                break

        if matched_key:
            val = int(matched_val) if matched_val.isdigit() else matched_val
            await _set_user_setting(user_id, matched_key, val)

        text, keyboard = _build_main_menu(user_id)
        await editMessage(query.message, text, keyboard)

    elif data.startswith("us_set_text_"):
        key = data.replace("us_set_text_", "")
        _awaiting_text[user_id] = key
        if key == KEY_INTRO_TEXT:
            prompt = "📝 <b>Reply with your Intro Subtitle text:</b>\n<i>Example: Telegram @YourChannel</i>"
        elif key == KEY_AUDIO_TAG_TEXT:
            prompt = "🏷️ <b>Reply with your Audio Tag text:</b>\n<i>Example: @YourChannel</i>"
        else:
            prompt = "✏️ Reply with the value:"
        await editMessage(query.message, prompt)

    elif data == "us_back":
        text, keyboard = _build_main_menu(user_id)
        await editMessage(query.message, text, keyboard)

    elif data == "us_close":
        await deleteMessage(query.message)


# ─────────────────────────────────────────────
#  TEXT REPLY HANDLER
# ─────────────────────────────────────────────

async def user_settings_text_reply(client, message):
    user_id = message.from_user.id
    if user_id not in _awaiting_text:
        return

    key = _awaiting_text.pop(user_id)
    value = message.text.strip()
    await _set_user_setting(user_id, key, value)

    await message.reply(
        f"✅ <b>Setting saved!</b>\n"
        f"<code>{key}</code> → <code>{value}</code>\n\n"
        f"Use /mset to view all your settings."
    )


def _filter_awaiting_text(_, __, message):
    if message.from_user is None:
        return False
    return message.from_user.id in _awaiting_text


from pyrogram.filters import create as create_filter
awaiting_text_filter = create_filter(_filter_awaiting_text)

def add_handlers():
    bot.add_handler(MessageHandler(user_settings_cmd, filters=command("mset") & CustomFilters.authorized))
    bot.add_handler(CallbackQueryHandler(user_settings_cb, filters=regex(r"^us_")))
    bot.add_handler(MessageHandler(user_settings_text_reply, filters=awaiting_text_filter & CustomFilters.authorized))
