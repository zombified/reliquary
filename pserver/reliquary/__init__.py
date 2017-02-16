from plone.server import configure
from zope.i18nmessageid import MessageFactory

_ = MessageFactory('pserver.reliquary')


#app_settings = {
#    "debug": False
#}


def includeme(root):
    configure.scan("pserver.reliquary.install")
    configure.scan("pserver.reliquary.contenttypes")
    configure.scan("pserver.reliquary.services")
