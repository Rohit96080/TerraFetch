def classFactory(iface):
    from .plugin import TerraFetch
    return TerraFetch(iface)
