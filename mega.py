class MegaApi:
    def __init__(self, *args, **kwargs): pass
    def getVersion(self): return "1.0.0"

class MegaListener: pass

class MegaRequest:
    TYPE_LOGIN = 1
    TYPE_FETCH_NODES = 2
    TYPE_GET_PUBLIC_NODE = 3

class MegaTransfer: pass
class MegaError: pass
