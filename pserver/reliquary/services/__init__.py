from plone.server import configure
from plone.server.api.service import Service
from plone.server.interfaces import ISite
from plone.server.browser import Response

import logging
logger = logging.getLogger(__name__)


@configure.service(
    context=ISite,
    name='@autoindex',
    method='GET',
    permission='plone.AccessContent')
class AutoIndex(Service):
    async def __call__(self):
        return Response(response='some <strong>html</strong>',
                        headers={
                            "Content-Type": "text/html"
                        },
                        status=200)
