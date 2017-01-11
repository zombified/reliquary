import bz2
import datetime
import gzip
import hashlib
import logging
import os
import re
import requests
import transaction

from mimetypes import guess_type
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response

from reliquary.models import (
    Channel,
    DBSession,
    DebInfo,
    FileCache,
    Index,
    Relic,
)


logger = logging.getLogger(__name__)


def fetch_channel_from_name(name):
    if not name:
        return None

    try:
        channelobj = DBSession.query(Channel) \
                              .filter_by(name=name) \
                              .one()
    except:
        logger.error('no channel object, or more than one found for "{}"'
                     .format(name))
        return None

    return channelobj


def fetch_index_from_name(channelobj, name):
    if not name:
        return None

    try:
        indexobj = DBSession.query(Index) \
                            .filter_by(channel_id=channelobj.uid, name=name) \
                            .one()
    except:
        logger.error('no index object, or more than one found for {}'
                     .format(name))
        return None

    return indexobj


def fetch_index_from_names(channel, index):
    channelobj = fetch_channel_from_name(channel)
    return fetch_index_from_name(channelobj, index)


def validate_reliquary_location(req, channel, index, relic_name=None):
    if not channel or not index:
        return HTTPNotFound()

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
    indexobj = fetch_index_from_names(channel, index)
    if not indexobj:
        return

    relics = DBSession.query(Relic) \
                      .filter_by(index_id=indexobj.uid, name=relic_name)
    # doesn't exist locally yet
    if relics.count() <= 0:
        # get valid paths, if there are valid paths to be had
        pathcheck = validate_reliquary_location(req, channel, index, relic_name=relic_name)  # noqa
        if type(pathcheck) == Response:
            return
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
                                index_id=indexobj.uid,
                                name=relic_name,
                                mtime=str(os.path.getmtime(relic_path)),
                                size=os.path.getsize(relic_path)))


def download_response(req, channel, index, relic_name):
    if not channel or not index or not relic_name:
        return HTTPNotFound()

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


# naming convention based on: https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Source
# returns a tuple of the following values:
#   2. name
#   3. version
#   4. arch
#   5. ext
def split_debian_name(name):
    # if the package name doesn't conform to this, it's probably not a valid
    # package name
    # group 1 = package name
    # group 2 = version name
    # group 3 = arch
    # group 4 = ext
    basicre = re.compile('^([a-z0-9+-.][a-z0-9+-.]+?)_([a-z0-9+-.][a-z0-9+-.]+?)(?:_([a-z0-9+-.][a-z0-9+-.]+?))?\.((?:orig\.)?tar\.gz|diff\.gz|dsc|deb)$')  # noqa
    result = basicre.search(name)
    if result:
        return (result.group(1), result.group(2), result.group(3), result.group(4))  # noqa
    return None


# 'compression' can be one of None, 'gz', or 'bz2'
# if 'force' is True, the data is not pulled from the database
def generate_debian_package_index(channel, index, arch, compression=None, force=False):
    basekey = '{}-{}-{}-'.format(channel, index, arch)
    key = basekey
    key += compression if compression else 'none'
    if not force:
        try:
            cacheddata = DBSession.query(FileCache).filter_by(key=key).one_or_none()
            if cacheddata:
                return (cacheddata.value,
                        cacheddata.mtime,
                        cacheddata.size,
                        cacheddata.md5sum,
                        cacheddata.sha1,
                        cacheddata.sha256)
        except:
            logger.error('multiple values with cache key "{}"'.format(key))
            return None
    else:
        with transaction.manager:
            DBSession.query(FileCache).filter(key=key).delete()

    # since the request is for a compressed file, check to see if we have a cached
    # uncompressed file first, and base our compressed one off of that...
    # mainly so the cached files remain in sync in terms of content
    if compression:
        uncompressedkey = basekey + 'none'
        try:
            cacheddata = DBSession.query(FileCache).filter_by(key=uncompressedkey).one_or_none()
            if cacheddata:
                bytedata = cacheddata.value
                if compression == "gz":
                    finaldata = gzip.compress(bytedata)
                elif compression == "bz2":
                    finaldata = bz2.compress(bytedata)
                else:
                    finaldata = bytedata

                mtime = datetime.datetime.utcnow()
                size = len(finaldata)
                md5sum = hashlib.md5(finaldata).hexdigest()
                sha1 = hashlib.sha1(finaldata).hexdigest()
                sha256 = hashlib.sha256(finaldata).hexdigest()
                newcacheddata = FileCache(
                    key=key,
                    value=finaldata,
                    mtime=mtime,
                    size=size,
                    md5sum=md5sum,
                    sha1=sha1,
                    sha256=sha256)
                with transaction.manager:
                    DBSession.add(newcacheddata)

                return (finaldata, mtime, size, md5sum, sha1, sha256)
        except:
            logger.error('multiple values with cache key "{}"'.format(uncompressedkey))
            return None


    # generate and cache Package file
    lines = []
    archobjs = DBSession.query(Relic, DebInfo) \
                        .filter(Relic.uid == DebInfo.relic_id) \
                        .filter(DebInfo.architecture.ilike('%{0}%'.format(arch)))
    for relic, debinfo in archobjs:
        # we're possibly pulling only partial matches, so this just confirms the
        # selection choice
        arches = [a.lower().strip() for a in debinfo.architecture.split()]
        if arch not in arches:
            continue

        lines.append("Package: {}".format(debinfo.package))
        if debinfo.source:
            lines.append("Source: {}".format(debinfo.source))
        lines.append("Version: {}".format(debinfo.version))
        if debinfo.section:
            lines.append("Section: {}".format(debinfo.section))
        if debinfo.section:
            lines.append("Priority: {}".format(debinfo.priority))
        lines.append("Architecture: {}".format(debinfo.architecture))
        if debinfo.essential:
            lines.append("Essential: {}".format(debinfo.essential))
        if debinfo.depends:
            lines.append("Depends: {}".format(debinfo.depends))
        if debinfo.recommends:
            lines.append("Recommends: {}".format(debinfo.recommends))
        if debinfo.suggests:
            lines.append("Suggests: {}".format(debinfo.suggests))
        if debinfo.enhances:
            lines.append("Enhances: {}".format(debinfo.enhances))
        if debinfo.pre_depends:
            lines.append("Pre-Depends: {}".format(debinfo.pre_depends))
        if debinfo.installed_size:
            lines.append("Installed-Size: {}".format(debinfo.installed_size))
        lines.append("Maintainer: {}".format(debinfo.maintainer))
        lines.append("Description: {}".format(debinfo.description))
        if debinfo.homepage:
            lines.append("Homepage: {}".format(debinfo.homepage))
        if debinfo.built_using:
            lines.append("Built-Using: {}".format(debinfo.built_using))
        lines.append("Filename: {}".format(debinfo.filename))
        lines.append("Size: {}".format(relic.size))
        lines.append("MD5Sum: {}".format(debinfo.md5sum))
        lines.append("SHA1: {}".format(debinfo.sha1))
        lines.append("SHA256: {}".format(debinfo.sha256))
        lines.append("SHA512: {}".format(debinfo.sha512))
        lines.append("Description-md5: {}".format(debinfo.description_md5))
        if debinfo.multi_arch:
            lines.append("Multi-Arch: {}".format(debinfo.multi_arch))
        lines.append("")

    data = "\n".join(lines)
    bytedata = data.encode()
    if compression == "gz":
        finaldata = gzip.compress(bytedata)
    elif compression == "bz2":
        finaldata = bz2.compress(bytedata)
    else:
        finaldata = bytedata

    mtime = datetime.datetime.utcnow()
    size = len(finaldata)
    md5sum = hashlib.md5(finaldata).hexdigest()
    sha1 = hashlib.sha1(finaldata).hexdigest()
    sha256 = hashlib.sha256(finaldata).hexdigest()
    newcacheddata = FileCache(
        key=key,
        value=finaldata,
        mtime=mtime,
        size=size,
        md5sum=md5sum,
        sha1=sha1,
        sha256=sha256)
    with transaction.manager:
        DBSession.add(newcacheddata)

    return (finaldata, mtime, size, md5sum, sha1, sha256)


def get_unique_architectures_set(index_id):
    arches = set()
    relics = DBSession.query(Relic).filter_by(index_id=index_id)
    for relic in relics:
        parts = split_debian_name(relic.name)
        if not parts or not parts[2]:
            continue
        arches.add(parts[2])

    return arches


def generate_debian_arch_release_index(arch):
    data = """Archive: reliquary
Component: main
Origin: reliquary
Label: reliquary
Architecture: {architecture}""".format(architecture=arch)
    mtime = datetime.datetime.utcnow()
    size = len(data)
    bytedata = data.encode()
    md5sum = hashlib.md5(bytedata).hexdigest()
    sha1 = hashlib.sha1(bytedata).hexdigest()
    sha256 = hashlib.sha256(bytedata).hexdigest()
    return (data, mtime, size, md5sum, sha1, sha256)


def get_debian_release_data(index_id):
    lines = []

    # Suite -- indicates one of 'oldstable', 'stable', 'testing', 'unstable',
    #   'experimental' with optional suffixes such as '-updates'
    # for now, fixed to 'stable'
    # (required)
    lines.append("Suite: stable")

    # Codename -- describe codename of the release
    # for now, fixed to 'reliquary'
    # (required)
    lines.append("Codename: reliquary")

    # Origin -- describe origin of the release
    # for now, fixed to 'reliquary'
    # (optional)
    lines.append("Origin: reliquary")

    # Architectures -- what are all the different architectures for packages
    #   being managed?
    # (required)
    unique_arches = get_unique_architectures_set(index_id)
    arches = []
    for a in unique_arches:
        arches.append(a)
    lines.append("Architectures: {}".format(" ".join(arches)))

    # Components -- this is a fixed and static value for now
    # (required)
    lines.append("Components: main")

    # Date -- the time the release file was created in UTC
    # (required)
    utcnow = "{:%a, %b %Y %H:%M:%S +0000}".format(datetime.datetime.utcnow())
    lines.append("Date: {}".format(utcnow))

    # MD5Sum/SHA1/SHA256/SHA512 -- lists of indices and the hash and size for them
    # each line contains white space separated values:
    #   1. checksum in the corresponding format
    #   2. size of the file
    #   3. filename relative to the directory of the Release file
    indexobj = DBSession.query(Index).filter_by(uid=index_id).one()
    index = indexobj.name
    channel = DBSession.query(Channel).filter_by(uid=indexobj.channel_id).one().name
    arches = get_unique_architectures_set(index_id)
    md5sums = []
    sha1s = []
    sha256s = []
    for arch in arches:
        package = generate_debian_package_index(channel, index, arch)
        packagegz = generate_debian_package_index(channel, index, arch, compression='gz')
        packagebz2 = generate_debian_package_index(channel, index, arch, compression='bz2')
        release = generate_debian_arch_release_index(arch)
        # uncompressed
        if not package:
            logger.error("Failed to get package details for debian/{}/dist/{}/[In]Release ({})".format(channel, index, arch))
        else:
            md5sums.append(" {} {} {}".format(package[3], str(package[2]).rjust(15), "main/binary-{}/Packages".format(arch)))
            sha1s.append(" {} {} {}".format(package[4], str(package[2]).rjust(15), "main/binary-{}/Packages".format(arch)))
            sha256s.append(" {} {} {}".format(package[5], str(package[2]).rjust(15), "main/binary-{}/Packages".format(arch)))
        # gz
        if not packagegz:
            logger.error("Failed to get package.gz details for debian/{}/dist/{}/[In]Release ({})".format(channel, index, arch))
        else:
            md5sums.append(" {} {} {}".format(packagegz[3], str(packagegz[2]).rjust(15), "main/binary-{}/Packages.gz".format(arch)))
            sha1s.append(" {} {} {}".format(packagegz[4], str(packagegz[2]).rjust(15), "main/binary-{}/Packages.gz".format(arch)))
            sha256s.append(" {} {} {}".format(packagegz[5], str(packagegz[2]).rjust(15), "main/binary-{}/Packages.gz".format(arch)))
        # bz2
        if not packagebz2:
            logger.error("Failed to get package.bz2 details for debian/{}/dist/{}/[In]Release ({})".format(channel, index, arch))
        else:
            md5sums.append(" {} {} {}".format(packagebz2[3], str(packagebz2[2]).rjust(15), "main/binary-{}/Packages.bz2".format(arch)))
            sha1s.append(" {} {} {}".format(packagebz2[4], str(packagebz2[2]).rjust(15), "main/binary-{}/Packages.bz2".format(arch)))
            sha256s.append(" {} {} {}".format(packagebz2[5], str(packagebz2[2]).rjust(15), "main/binary-{}/Packages.bz2".format(arch)))
        # release
        if not release:
            logger.error("Failed to get release details for debian/{}/dist/{}/[In]Release ({})".format(channel, index, arch))
        else:
            md5sums.append(" {} {} {}".format(release[3], str(release[2]).rjust(15), "main/binary-{}/Release".format(arch)))
            sha1s.append(" {} {} {}".format(release[4], str(release[2]).rjust(15), "main/binary-{}/Release".format(arch)))
            sha256s.append(" {} {} {}".format(release[5], str(release[2]).rjust(15), "main/binary-{}/Release".format(arch)))

    lines.append("MD5Sum:")
    lines.append("\n".join(md5sums))
    lines.append("SHA1:")
    lines.append("\n".join(sha1s))
    lines.append("SHA256:")
    lines.append("\n".join(sha256s))

    # Acquire-By-Hash -- an alternative method for clients, this is just an
    #   indicator for whether or not the server supports this
    # for now, reliquary does not support this
    lines.append("Acquire-By-Hash: no")

    return "\n".join(lines)
