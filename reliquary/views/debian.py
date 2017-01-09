import bz2
import logging
import gzip
import time

from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.view import view_config

from reliquary.models import DBSession, Index, Relic
from reliquary.utils import (
    download_response,
    fetch_channel_from_name,
    fetch_index_from_names,
    generate_debian_package_index,
    split_debian_name,
)


logger = logging.getLogger(__name__)


def fetch_channel_index_items(req, channelobj, route_name):
    items = []
    indices = DBSession.query(Index).filter_by(channel_id=channelobj.uid)
    for idx in indices:
        items.append(dict(
            url=req.route_url(route_name,
                              channel=channelobj.name,
                              index=idx.name),
            text=idx.name,
            cls="folder"
        ))
    items.sort(key=lambda x: x["text"])
    return items


@view_config(
    route_name='debian_channelindex',
    renderer='templates/debian_index.pt',
    request_method='GET',
    permission='view')
def debian_channelindex(req):
    channel = req.matchdict.get('channel', None)
    channelobj = fetch_channel_from_name(channel)
    if not channelobj:
        return HTTPNotFound()

    items = [dict(url=req.route_url('debian_distrootindex', channel=channel),
                  text="dist",
                  cls="folder"),
             dict(url=req.route_url('debian_poolrootindex', channel=channel),
                  text="pool",
                  cls="folder")]

    return dict(
        page_title="Index of /{}".format(channel),
        items=items,
        datetime_generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        show_updir=False,
    )


@view_config(
    route_name='debian_poolrootindex',
    renderer='templates/debian_index.pt',
    request_method='GET',
    permission='view')
def debian_poolrootindex(req):
    channel = req.matchdict.get('channel', None)
    channelobj = fetch_channel_from_name(channel)
    if not channelobj:
        return HTTPNotFound()

    items = fetch_channel_index_items(req, channelobj, "debian_pooldistindex")
    return dict(
        page_title="Index of /{}/pool/".format(channel),
        items=items,
        datetime_generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        show_updir=True,
    )


@view_config(
    route_name='debian_pooldistindex',
    renderer='templates/debian_index.pt',
    request_method='GET',
    permission='view')
def debian_pooldistindex(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    items = []
    relics = DBSession.query(Relic).filter_by(index_id=indexobj.uid)
    for relic in relics:
        items.append(dict(
            url=req.route_url('debian_poolpackage', channel=channel, index=index, relic_name=relic.name),
            text=relic.name,
            cls="file"
        ))
    items.sort(key=lambda x: x["text"])

    return dict(
        page_title="Index of /{}/pool/{}/".format(channel, index),
        items=items,
        datetime_generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        show_updir=True,
    )


@view_config(
    route_name='debian_distrootindex',
    renderer='templates/debian_index.pt',
    request_method='GET',
    permission='view')
def debian_distrootindex(req):
    channel = req.matchdict.get('channel', None)
    channelobj = fetch_channel_from_name(channel)
    if not channelobj:
        return HTTPNotFound()

    items = fetch_channel_index_items(req, channelobj, "debian_distindex")
    return dict(
        page_title="Index of /{}/dist/".format(channel),
        items=items,
        datetime_generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        show_updir=True,
    )


@view_config(
    route_name='debian_distindex',
    renderer='templates/debian_index.pt',
    request_method='GET',
    permission='view')
def debian_distindex(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    items = [
        dict(url=req.route_url('debian_compindex',
                               channel=channel,
                               index=index),
             text="main",
             cls="folder"),
        dict(url=req.route_url('debian_distrelease',
                               channel=channel,
                               index=index),
             text="Release",
             cls="file"),
    ]

    return dict(
        page_title="Index of /{}/dist/{}/".format(channel, index),
        items=items,
        datetime_generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        show_updir=True,
    )


@view_config(
    route_name='debian_compindex',
    renderer='templates/debian_index.pt',
    request_method='GET',
    permission='view')
def debian_compindex(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    # need to determine unique architectures of packages available
    arches = set()
    relics = DBSession.query(Relic).filter_by(index_id=indexobj.uid)
    for relic in relics:
        parts = split_debian_name(relic.name)
        if not parts or not parts[2]:
            continue
        arches.add(parts[2])

    items = []
    for arch in arches:
        items.append(dict(
            url=req.route_url('debian_archindex',
                              channel=channel,
                              index=index,
                              arch=arch),
            text="binary-"+arch,
            cls="folder"))
    items.sort(key=lambda x: x["text"])

    return dict(
        page_title="Index of /{}/dist/{}/main/".format(channel, index),
        items=items,
        datetime_generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        show_updir=True,
    )


@view_config(
    route_name='debian_archindex',
    renderer='templates/debian_index.pt',
    request_method='GET',
    permission='view')
def debian_archindex(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    arch = req.matchdict.get('arch', None)

    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    items = [
        dict(url=req.route_url('debian_archrelease',
                               channel=channel,
                               index=index,
                               arch=arch),
             text="Release",
             cls="file"),
        dict(url=req.route_url('debian_archpackages',
                               channel=channel,
                               index=index,
                               arch=arch),
             text="Packages",
             cls="file"),
        dict(url=req.route_url('debian_archpackagesgz',
                               channel=channel,
                               index=index,
                               arch=arch),
             text="Packages.gz",
             cls="file"),
        dict(url=req.route_url('debian_archpackagesbz2',
                               channel=channel,
                               index=index,
                               arch=arch),
             text="Packages.bz2",
             cls="file"),
    ]
    items.sort(key=lambda x: x["text"])

    return dict(
        page_title="Index of /{}/dist/{}/main/binary-{}".format(channel, index, arch),
        items=items,
        datetime_generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        show_updir=True,
    )


@view_config(
    route_name='debian_poolpackage',
    request_method='GET',
    permission='view')
def debian_poolpackage(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    relic_name = req.matchdict.get('relic_name', None)

    if not channel or not index or not relic_name:
        return HTTPNotFound()

    return download_response(req, channel, index, relic_name)


@view_config(
    route_name='debian_archpackages',
    request_method='GET',
    permission='view')
def debian_archpackages(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    arch = req.matchdict.get('arch', None)

    if not channel or not index or not arch:
        return HTTPNotFound()

    arch = arch.lower().strip()

    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    packagestr = generate_debian_package_index(channel, index, arch)
    return Response(packagestr, content_type="text/plain", status_code=200)


@view_config(
    route_name='debian_archpackagesgz',
    request_method='GET',
    permission='view')
def debian_archpackagesgz(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    arch = req.matchdict.get('arch', None)

    if not channel or not index or not arch:
        return HTTPNotFound()

    arch = arch.lower().strip()

    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    packagestr = generate_debian_package_index(channel, index, arch)
    gzstr = gzip.compress(packagestr.encode())
    return Response(gzstr, content_type="application/gzip", status_code=200)


@view_config(
    route_name='debian_archpackagesbz2',
    request_method='GET',
    permission='view')
def debian_archpackagesbz2(req):
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    arch = req.matchdict.get('arch', None)

    if not channel or not index or not arch:
        return HTTPNotFound()

    arch = arch.lower().strip()

    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return HTTPNotFound()

    packagestr = generate_debian_package_index(channel, index, arch)
    bz2str = bz2.compress(packagestr.encode())
    return Response(bz2str, content_type="application/x-bzip2", status_code=200)
