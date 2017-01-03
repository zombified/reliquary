import os

from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.view import view_config

from reliquary.utils import validate_reliquary_location, download_response


@view_config(route_name='put_relic', request_method='PUT', permission='put')
def put_relic(req):
    # set path for relic from url parts
    channel = req.matchdict.get('channel', 'default')
    index = req.matchdict.get('index', 'default')
    relic_name = req.matchdict.get('relic_name', None)
    if not relic_name:
        return Response('{"status":"error","relic name not given"}',
                        content_type='application/json',
                        status_code=500)

    # get valid paths, if there are valid paths to be had
    pathcheck = validate_reliquary_location(
        req,
        channel,
        index,
        relic_name=relic_name)
    if type(pathcheck) == Response:
        return pathcheck
    reliquary, relic_folder, relic_path = pathcheck

    # create the channel/index if it doesn't exist
    if not os.path.exists(relic_folder):
        os.makedirs(relic_folder)

    # save relic to the path
    req.body_file.seek(0)
    with open(relic_path, 'wb') as fout:
        fout.write(req.body_file.read())

    return Response('{"status":"ok"}', content_type='application/json')


@view_config(route_name='get_relic', request_method='GET', permission='view')
def get_relic(req):
    # set path for relic from url parts
    channel = req.matchdict.get('channel', None)
    index = req.matchdict.get('index', None)
    relic_name = req.matchdict.get('relic_name', None)
    if not channel or not index or not relic_name:
        return HTTPNotFound()
    return download_response(req, channel, index, relic_name)
