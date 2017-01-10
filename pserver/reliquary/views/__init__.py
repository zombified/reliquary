import logging


logger = logging.getLogger(__name__)


from plone.server.configure import service
from plone.server.interfaces import ISite
from plone.server.browser import Response


@service(context=ISite, name='@autoindex', method='GET', permission='plone.AccessContent')
async def autoindex(ctx, req):
    return Response(response='some <strong>html</strong>',
                    headers={
                        "Content-Type": "text/html"
                    },
                    status=200)
