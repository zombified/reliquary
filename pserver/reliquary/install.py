from plone.server import configure
from plone.server.addons import Addon
from plone.server.registry import ILayers

import logging
logger = logging.getLogger(__name__)


RELIQUARY_LAYER = 'pserver.reliquary.interfaces.IReliquaryLayer'


@configure.addon(name="reliquary", title="Reliquary")
class ReliquaryAddon(Addon):

    @classmethod
    def install(self, request):
        logger.info("installing")
        registry = request.site_settings
        registry.for_interface(ILayers).active_layers |= {
            RELIQUARY_LAYER
        }

    @classmethod
    def uninstall(self, request):
        logger.info("uninstalling")
        registry = request.site_settings
        registry.for_interface(ILayers).active_layers -= {
            RELIQUARY_LAYER
        }
