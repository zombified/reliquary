from plone.server import configure
from plone.server.content import Item
from plone.server.interfaces import IItem
from zope import schema


# a relic is a set of metadata describing, and file data containing, an
# software/data distribution of some sort
class IRelic(IItem):
    mtime = schema.Text()
    size = schema.Int()


@configure.contenttype(
    portal_type='Relic',
    schema=IRelic,
    behaviors=[
        'plone.server.behaviors.dublincore.IDublinCore',
        'plone.server.behaviors.attachment.IAttachment',
    ])
class Relic(Item):
    pass
