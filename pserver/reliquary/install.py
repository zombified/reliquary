from plone.server.addons import Addon
from plone.server.registry import ILayers


RELIQUARY_LAYER = 'pserver.reliquary.interfaces.IReliquaryLayer'


class ReliquaryAddon(Addon):

    @classmethod
    def install(self, request):
        registry = request.site_settings
        registry.for_interface(ILayers).active_layers |= {
            RELIQUARY_LAYER
        }

    @classmethod
    def uninstall(self, request):
        registry = request.site_settings
        registry.for_interface(ILayers).active_layers -= {
            RELIQUARY_LAYER
        }
