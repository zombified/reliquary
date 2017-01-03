import os
import re
import requests
import transaction

from mimetypes import guess_type
from pyramid.response import Response

from reliquary.models import DBSession, Relic


def validate_reliquary_location(req, channel, index, relic_name=None):
    # make sure storage directory is set
    reliquary = req.registry.settings.get('reliquary.location', None)
    if not reliquary:
        return Response('{"status":"error","reliquary not configured"}',
                        content_type='application/json',
                        status_code=500)
    reliquary = os.path.normpath(reliquary)

    # make sure the location exists for the relic to be stored at (and
    # make sure the uploader isn't trying to bust out of the reliquary
    relic_folder = os.path.join(reliquary, channel, index)
    relic_folder = os.path.normpath(relic_folder)
    if not relic_folder.startswith(reliquary) or re.search(r'[^A-Za-z0-9_\-\/ \.]', relic_folder):  # noqa
        return Response('{"status":"error","invalid channel/index"}',  # noqa
                        content_type='application/json',
                        status_code=500)

    # if a relic_name is given, make sure it works as well
    relic_path = None
    if relic_name:
        relic_path = os.path.normpath(os.path.join(relic_folder, relic_name))
        if not relic_path.startswith(reliquary) or re.search(r'[^A-Za-z0-9_\-\/ \.]', relic_path):  # noqa
            return Response('{"status":"error","invalid relic name"}',  # noqa
                            content_type='application/json',
                            status_code=500)

    return (reliquary, relic_folder, relic_path)


def pypi_normalize_package_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def fetch_relic_if_not_exists(req, channel, index, relic_name, upstream):
    relics = DBSession.query(Relic) \
                      .filter_by(channel=channel, index=index, name=relic_name)
    # doesn't exist locally yet
    if relics.count() <= 0:
        # get valid paths, if there are valid paths to be had
        pathcheck = validate_reliquary_location(req, channel, index, relic_name=relic_name)  # noqa
        if type(pathcheck) == Response:
            return pathcheck
        reliquary, relic_folder, relic_path = pathcheck

        # create the channel/index if it doesn't exist
        if not os.path.exists(relic_folder):
            os.makedirs(relic_folder)

        # fetch
        resp = requests.get(upstream)

        # save
        with open(relic_path, 'wb') as fout:
            fout.write(resp.content)

        # index
        with transaction.manager:
            DBSession.add(Relic(dirty=False,
                                channel=channel,
                                index=index,
                                name=relic_name,
                                mtime=str(os.path.getmtime(relic_path)),
                                size=os.path.getsize(relic_path)))


def download_response(req, channel, index, relic_name):
    # get valid paths, if there are valid paths to be had
    pathcheck = validate_reliquary_location(
        req,
        channel,
        index,
        relic_name=relic_name)
    if type(pathcheck) == Response:
        return pathcheck
    reliquary, relic_folder, relic_path = pathcheck
    relic_abs_path = os.path.abspath(os.path.join(reliquary, relic_path))

    settings = req.registry.settings
    xsend_enabled = settings.get('reliquary.xsendfile_enabled', None) == 'true'
    xsend_frontend = settings.get('reliquary.xsendfile_frontend', 'nginx') \
                             .strip().lower()

    # TODO: implement other xsend implementations besides nginx
    if xsend_enabled and xsend_frontend != 'nginx':
        return Response('{"status":"not implemented yet -- only nginx xsend '
                        'support is enabled"}',
                        content_type='application/json')

    # header values for response
    mime_type, encoding = guess_type(relic_abs_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    content_length = str(os.path.getsize(relic_abs_path))
    headers = dict()
    headers['Content-Type'] = mime_type
    headers['Content-Disposition'] = 'attachment; filename="{}"'.format(relic_name)  # noqa
    headers['Content-Length'] = content_length
    if encoding:
        headers['Content-Encoding'] = encoding

    # only send back a response with xsend headers for proxy server
    # to handle
    if xsend_enabled and xsend_frontend == 'nginx':
        headers['X-Accel-Redirect'] = relic_abs_path
        return Response(headers=headers, status=200)

    # return the actual object in the response
    relic_fp = open(relic_abs_path, 'rb')
    return Response(body_file=relic_fp, headers=headers, status=200)


# based on commonjs packaging/1.1 spec (basically <name>-<semver>.<ext>)
def split_commonjs_name(name):
    namere = re.compile('^([\w\d\-\._]+)-((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[\da-z\-]+(?:\.[\da-z\-]+)*)?(?:\+[\da-z\-]+(?:\.[\da-z\-]+)*)?)\.((?:tar\.gz)|(?:tgz))$')
    # group 1 = name
    # group 2 = version
    # group 3 = extension
    result = namere.search(name)
    if not result:
        return (name, None, None)
    return (result.group(1), result.group(2), result.group(3))


# returns a tuple where the first 3 values are:
#   1. package name
#   2. version
#   3. extension
# or None for a value if it could not be determined.
# based on PEP-440, PEP-491, and observation of non-conforming names
def split_pypi_name(name):
    # old convention of naming packages on pypi
    # group 1 = package name
    # group 2 = entire version compatible with PEP-440
    # group 3 = supported python version
    # group 4 = extension (one of tgz, tar.gz, zip, tar.bz2, tbz2, egg, whl)
    # ex: pytz-2016.10-py2.4.egg, pytz-2016.10.tar.bz2, pytz-2016.10.tar.gz,
    #     pytz-2016.10.zip
    basicre = re.compile('^([\w\d\.\-\_]+)-((?:(?:\d+!)?(?:\d+)(?:\.\d+)*)(?:(?:a|b|rc)?\d+)?(?:\.post\d+)?(?:\.dev\d+)?(?:\+[a-zA-Z0-9\.]+)?)(?:-([\w\d\.]+))?\.((?:tgz)|(?:tar\.gz)|(?:zip)|(?:tar.bz2)|(?:tbz2)|(?:egg))$')
    result = basicre.search(name)
    if result:
        return (result.group(1), result.group(2), result.group(4))

    # Wheel standard naming (PEP-491)
    # group 1 = package name
    # group 2 = version
    # group 3 = build tag (optional)
    # group 4 = python tag
    # group 5 = abi tag
    # group 6 = platform tag
    # ex: zest.releaser-6.7.1-1buildtag-py2.py3.py27.py35-none-any.whl
    whlre = re.compile('^([\w\d\.\-_]+)-((?:(?:\d+!)?(?:\d+)(?:\.\d+)*)(?:(?:a|b|rc)?\d+)?(?:\.post\d+)?(?:\.dev\d+)?(?:\+[a-zA-Z0-9\.]+)?)(?:-(\d[\w\d]*))?-((?:[\w\d]+(?:\.[\w\d]+)*))-([\w\d]+)-([\w\d_]+)\.whl$')
    result = whlre.search(name)
    if result:
        return (result.group(1), result.group(2), 'whl')

    # if both the above fail, then simply try to get a name, 1 or more segment
    # version, and (hopefully) an extension
    # group 1 = package name
    # group 2 = version
    # group 3 = extention/remainder
    simplere = re.compile('^(.*)-(\d+(?:\.\d+)+)(.*)$')
    result = simplere.search(name)
    if result:
        return (result.group(1), result.group(2), result.group(3).strip('.'))

    # and if none of the above match, then simply return the whole value as the
    # package name, with no version, and no extension
    return (name, None, None)