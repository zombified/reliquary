from plone.server import configure
from plone.server.api.service import Service
from plone.server.interfaces import ISite
from plone.server.browser import Response

from pserver.reliquary.contenttypes.relic import Relic

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




#@configure.service(
#    context=ISite,
#    name="@addrelic",
#    method="PUT",
#    permission="plone.AddContent")
#async def add_relic(context, request):
#    # need:
#    #   1. file name
#    #   2. mtime
#    #   3. size
#    #   4. file data
#
#    import pdb; pdb.set_trace()
#
#    return {}
