from plone.server.commands import Command

import logging
logger = logging.getLogger(__name__)


class Indexer(Command):
    def get_parser(self):
        parser = super(Indexer, self).get_parser()

        return parser

    def run(self, arguments, settings, app):
        logger.info("running indexer")
        pass
