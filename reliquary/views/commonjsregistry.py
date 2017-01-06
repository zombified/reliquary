import json
import requests

from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.view import view_config

from reliquary.models import DBSession, Relic
from reliquary.utils import (
    download_response,
    fetch_index_from_names,
    fetch_relic_if_not_exists,
    split_commonjs_name,
)


@view_config(
    route_name='commonjs_registry_root',
    request_method='GET',
    permission='view')
def commonjs_registry_root(req):
    channel = req.matchdict.get('channel', 'default')
    index = req.matchdict.get('index', 'default')

    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    relics = DBSession.query(Relic).filter_by(index_id=indexobj.uid)
    uniqrelics = {}
    for relic in relics:
        matches = split_commonjs_name(relic.name)
        relicname = None
        if not matches:
            relicname = relic.name
        else:
            relicname = matches[0]
        relic_url = req.route_url('commonjs_registry_package_root',
                                  channel=channel,
                                  index=index,
                                  package=relicname)
        if relicname not in uniqrelics:
            uniqrelics[relicname] = relic_url

    return Response(json.dumps(uniqrelics, sort_keys=True, indent=2),
                    content_type='application/json',
                    status_code=200)


@view_config(
    route_name='commonjs_registry_package_root',
    request_method='GET',
    permission='view')
def commonjs_registry_package_root(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    package = req.matchdict.get('package', None)

    if not channel or not index or not package:
        return HTTPNotFound()

    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    # this gets all packages that start with the requested package name,
    # but it may include more than the intended package -- from here,
    # each relic name needs to be broken down into it's name and version
    # then compared with the the given name
    results = DBSession.query(Relic) \
                       .filter_by(index_id=indexobj.uid) \
                       .filter(Relic.name.startswith(package))
    packageobjroot = dict(name=package, versions=dict())
    for relic in results:
        name, version, _ = split_commonjs_name(relic.name)
        if name.strip().lower() == package.strip().lower():
            relic_url = req.route_url('get_relic',
                                      channel=channel,
                                      index=index,
                                      relic_name=relic.name)
            packageobjroot["versions"][version] = dict(
                name=name,
                version=version,
                dist=dict(tarball=relic_url)
            )

    return Response(json.dumps(packageobjroot, sort_keys=True, indent=2),
                    content_type='application/json',
                    status_code=200)


@view_config(
    route_name='commonjs_registry_package_version',
    request_method='GET',
    permission='view')
def commonjs_registry_package_version(req):
    channel = req.matchdict.get('channel', 'default')
    index = req.matchdict.get('index', 'default')
    package = req.matchdict.get('package', None)
    version = req.matchdict.get('version', None)

    if not channel or not index or not package or not version:
        return HTTPNotFound()

    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    # this gets all packages that start with the requested package name,
    # but it may include more than the intended package -- from here,
    # each relic name needs to be broken down into it's name and version
    # then compared with the the given name
    results = DBSession.query(Relic) \
                       .filter_by(index_id=indexobj.uid) \
                       .filter(Relic.name.startswith(package))
    packageversionobj = dict()
    for relic in results:
        name, pversion, _ = split_commonjs_name(relic.name)
        if name.strip().lower() == package.strip().lower() \
                and pversion == version:
            relic_url = req.route_url('get_relic',
                                      channel=channel,
                                      index=index,
                                      relic_name=relic.name)
            packageversionobj['name'] = name
            packageversionobj['version'] = version
            packageversionobj['dist'] = dict(tarball=relic_url)

    return Response(json.dumps(packageversionobj, sort_keys=True, indent=2),
                    content_type='application/json',
                    status_code=200)


@view_config(
    route_name='commonjs_proxy_registry_root',
    request_method='GET',
    permission='view')
def commonjs_proxy_registry_root(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    if not channel or not index:
        return Response('{"status":"error","index/channel not found"}',
                        content_type='application/json',
                        status_code=404)

    # this really is just a proxy for the upstream.
    # TODO: configurable upstream
    # TODO: more granular permissions for this view to prevent abuse
    # TODO: temp redirect to self-hosted url instead of proxy url
    resp = requests.get('http://registry.npmjs.org/-/all')
    if resp.status_code != 200:
        return Response('{"status":"error","upstream had error '+str(resp.status_code)+'"}',  # noqa
                        content_type='application/json',
                        status_code=404)

    return Response(resp.text, content_type='text/html')


@view_config(
    route_name='commonjs_proxy_registry_package_root',
    request_method='GET',
    permission='view')
def commonjs_proxy_registry_package_root(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    package = req.matchdict.get('package', None)
    if not channel or not index or not package:
        return Response('{"status":"error","package not found"}',
                        content_type='application/json',
                        status_code=404)

    # this really is just a proxy for the upstream.
    # TODO: configurable upstream
    # TODO: more granular permissions for this view to prevent abuse
    # TODO: temp redirect to self-hosted url instead of proxy url
    resp = requests.get('http://registry.npmjs.org/{}/'.format(package))
    if resp.status_code != 200:
        return Response('{"status":"error","upstream had error '+str(resp.status_code)+'"}',  # noqa
                        content_type='application/json',
                        status_code=404)

    # need to replace all versions/<version>/<dist>/tarball urls with urls for
    # the reliquary proxy to resolve instead of whatever the npmjs registry is
    # indicating should be the tarball location.
    try:
        data = resp.json()
        for version, obj in data["versions"].items():
            dist = obj.get("dist", None)
            if not dist:
                return Response('{"status":"error - no dist"}',
                                content_type='application/json',
                                status_code=500)
            tarball = dist.get("tarball", None)
            if not tarball:
                return Response('{"status":"error - no tarball"}',
                                content_type='application/json',
                                status_code=500)
            tarball = tarball.replace('\\', '')
            newurl = req.route_url('commonjs_proxy_package',
                                   channel=channel,
                                   index=index,
                                   package=package,
                                   version=version,
                                   _query=[('upstream', tarball)])
            data["versions"][version]["dist"]["tarball"] = newurl
    except KeyError:
        return Response('{"status":"error - no versions"}',
                        content_type='application/json',
                        status_code=500)
    except ValueError:
        return Response('{"status":"error decoding of upstream json failed"}',
                        content_type='application/json',
                        status_code=500)

    return Response(json.dumps(data, sort_keys=True, indent=2),
                    content_type='application/json',
                    status_code=200)


@view_config(
    route_name='commonjs_proxy_registry_package_version',
    request_method='GET',
    permission='view')
def commonjs_proxy_registry_package_version(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    package = req.matchdict.get('package', None)
    version = req.matchdict.get('version', None)
    if not channel or not index or not package or not version:
        return Response('{"status":"error","package/version not found"}',
                        content_type='application/json',
                        status_code=404)

    # this really is just a proxy for the upstream.
    # TODO: configurable upstream
    # TODO: more granular permissions for this view to prevent abuse
    # TODO: temp redirect to self-hosted url instead of proxy url
    resp = requests.get('http://registry.npmjs.org/{}/{}/'.format(package, version))
    if resp.status_code != 200:
        return Response('{"status":"error","upstream had error '+str(resp.status_code)+'"}',  # noqa
                        content_type='application/json',
                        status_code=404)

    # need to replace all versions/<version>/<dist>/tarball urls with urls for
    # the reliquary proxy to resolve instead of whatever the npmjs registry is
    # indicating should be the tarball location.
    try:
        data = resp.json()
        dist = data.get("dist", None)
        if not dist:
            return Response('{"status":"error - no dist"}',
                            content_type='application/json',
                            status_code=500)
        tarball = dist.get("tarball", None)
        if not tarball:
            return Response('{"status":"error - no tarball"}',
                            content_type='application/json',
                            status_code=500)
        tarball = tarball.replace('\\', '')
        newurl = req.route_url('commonjs_proxy_package',
                               channel=channel,
                               index=index,
                               package=package,
                               version=version,
                               _query=[('upstream', tarball)])
        data["dist"]["tarball"] = newurl
    except ValueError:
        return Response('{"status":"error decoding of upstream json failed"}',
                        content_type='application/json',
                        status_code=500)

    return Response(json.dumps(data, sort_keys=True, indent=2),
                    content_type='application/json',
                    status_code=200)


@view_config(
    route_name='commonjs_proxy_package',
    request_method='GET',
    permission='view')
def commonjs_proxy_package(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    package = req.matchdict.get('package', None)
    version = req.matchdict.get('version', None)
    if not channel or not index or not package or not version:
        return Response('{"status":"error","package/version not found"}',
                        content_type='application/json',
                        status_code=404)

    upstream = req.params.get("upstream", None)
    if not upstream:
        return Response('{"status":"error","no upstream url given"}',
                        content_type='application/json',
                        status_code=500)

    # this is the naming convention for npm packages, and, for the moment, all
    # package distributions are supposed to be tarball's with the ext 'tgz'
    relic_name = "{}-{}.tgz".format(package, version)

    fetch_relic_if_not_exists(req, channel, index, relic_name, upstream)
    return download_response(req, channel, index, relic_name)
