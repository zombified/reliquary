import requests

from pyramid.response import Response
from pyramid.url import route_url
from pyramid.view import view_config

from reliquary.models import DBSession, Relic
from reliquary.utils import (
    download_response,
    fetch_relic_if_not_exists,
    pypi_normalize_package_name,
    split_pypi_name,
)


@view_config(
    route_name='pypi_simple',
    renderer='templates/pypi_simple.pt',
    request_method='GET',
    permission='view')
def pypi_simple(req):
    channel = req.matchdict.get('channel', 'default')
    index = req.matchdict.get('index', 'default')

    lines = []
    relics = DBSession.query(Relic).filter_by(channel=channel, index=index)
    uniqrelics = {}
    for relic in relics:
        matches = split_pypi_name(relic.name)
        # if a name couldn't be satisfactorly extracted, use the the whole
        # relic name as the package name
        if not matches:
            uniqrelics[relic.name] = True
        else:
            uniqrelics[matches[0]] = True
    for relic, _ in uniqrelics.items():
        lines.append("<a href='{0}'>{0}</a><br/>".format(
                     pypi_normalize_package_name(relic)))

    lines.sort()

    return dict(lines=lines)


@view_config(
    route_name='pypi_simple_package',
    renderer='templates/pypi_simple_package.pt',
    request_method='GET',
    permission='view')
def pypi_simple_package(req):
    channel = req.matchdict.get('channel', 'default')
    index = req.matchdict.get('index', 'default')
    package = req.matchdict.get('package', None)
    if not package:
        return Response('{"status":"error","package not found"}',
                        content_type='application/json',
                        status_code=404)
    package = pypi_normalize_package_name(package)

    lines = []
    relics = DBSession.query(Relic) \
                      .filter_by(channel=channel, index=index)
    matched = []
    for relic in relics:
        rparts = split_pypi_name(relic.name)
        normname = pypi_normalize_package_name(rparts[0])
        if package == normname:
            matched.append((relic.name, normname))
    matched.sort(key=lambda x: x[1])

    for relic in matched:
        packageurl = route_url('get_relic',
                               req,
                               channel=channel,
                               index=index,
                               relic_name=relic[0])
        lines.append("<a href='{0}' rel='internal'>{1}</a><br/>".format(
                     packageurl, relic[0]))

    return dict(lines=lines)


@view_config(
    route_name='pypi_proxy_simple',
    request_method='GET',
    permission='view')
def pypi_proxy_simple(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    if not channel or not index:
        return Response('{"status":"error","channel/index not found"}',
                        content_type='application/json',
                        status_code=404)

    # this really is just a proxy for the upstream.
    # TODO: configurable upstream
    # TODO: more granular permissions for this view to prevent abuse
    # TODO: temp redirect to self-hosted url instead of proxy url
    resp = requests.get('https://pypi.python.org/simple/')
    if resp.status_code != 200:
        return Response('{"status":"error","upstream had error '+str(resp.status_code)+'"}',  # noqa
                        content_type='application/json',
                        status_code=404)

    return Response(resp.text, content_type='text/html')


@view_config(
    route_name='pypi_proxy_simple_package',
    request_method='GET',
    permission='view')
def pypi_proxy_simple_package(req):
    channel = req.matchdict.get('channel', 'default')
    index = req.matchdict.get('index', 'default')
    package = req.matchdict.get('package', None)
    if not channel or not index or not package:
        return Response('{"status":"error","package not found"}',
                        content_type='application/json',
                        status_code=404)

    # this really is just a proxy for the upstream.
    # TODO: configurable upstream
    # TODO: more granular permissions for this view to prevent abuse
    # TODO: temp redirect to self-hosted url instead of proxy url
    resp = requests.get('https://pypi.python.org/simple/{0}/'.format(package))
    if resp.status_code != 200:
        return Response('{"status":"error","upstream had error '+str(resp.status_code)+'"}',  # noqa
                        content_type='application/json',
                        status_code=404)

    return Response(resp.text, content_type='text/html')


@view_config(
    route_name='pypi_proxy_package',
    request_method='GET',
    permission='view')
def pypi_proxy_package(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    parta = req.matchdict.get('parta', None)
    partb = req.matchdict.get('partb', None)
    hashval = req.matchdict.get('hash', None)
    package = req.matchdict.get('package', None)
    if not channel or not index or not parta or not partb or not hashval or not package:  # noqa
        return Response('{"status":"error","package not found"}',
                        content_type='application/json',
                        status_code=404)

    packageparts = package.split('#')
    relic_name = packageparts[0]
    upstream = "https://pypi.python.org/packages/{0}/{1}/{2}/{3}".format(parta, partb, hashval, package)

    fetch_relic_if_not_exists(req, channel, index, relic_name, upstream)
    return download_response(req, channel, index, relic_name)
