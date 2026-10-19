def classFactory(iface):
    from .plugin import SentinelLoader
    return SentinelLoader(iface)
