from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.security import forget
from pyramid.view import forbidden_view_config, view_config

from .api import get_relic, put_relic
from .autoindex import autoindex
from .pypi import (
    pypi_simple,
    pypi_simple_package,
    pypi_proxy_simple,
    pypi_proxy_simple_package,
    pypi_proxy_package,
)

from reliquary.models import DBSession, Relic


@forbidden_view_config()
def forbidden_view(req):
    resp = HTTPUnauthorized()
    resp.headers.update(forget(req))
    return resp


@view_config(
    route_name='home',
    renderer='templates/home.pt',
    request_method='GET',
    permission='view')
def home(req):
    result = DBSession.query(Relic.channel, Relic.index).distinct(Relic.channel, Relic.index)
    indices = []
    for relic in result:
        indices.append(dict(channel=relic.channel, name=relic.index))
    indices.sort(key=lambda x: x['channel']+x['name'])
    return dict(indices=indices)
