from plone.server import configure
from plone.server.content import Folder
from plone.server.interfaces import IItem
from zope import schema


# a relic is a set of metadata describing, and file data containing, an
# software/data distribution of some sort
class IRelicIndex(IItem):
    pass


@configure.contenttype(
    portal_type='RelicIndex',
    schema=IRelicIndex,
    behaviors=[
        'plone.server.behaviors.dublincore.IDublinCore',
    ],
    allowed_types=[
        'Relic',
    ])
class RelicIndex(Folder):
    pass
