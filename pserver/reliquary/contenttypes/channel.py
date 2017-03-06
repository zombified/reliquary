from plone.server import configure
from plone.server.content import Folder
from plone.server.interfaces import IItem
from zope import schema


# a relic is a set of metadata describing, and file data containing, an
# software/data distribution of some sort
class IChannel(IItem):
    pass


@configure.contenttype(
    portal_type='Channel',
    schema=IChannel,
    behaviors=[
        'plone.server.behaviors.dublincore.IDublinCore',
    ],
    allowed_types=[
        'RelicIndex',
    ])
class Channel(Folder):
    pass
