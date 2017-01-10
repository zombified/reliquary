import hashlib
import optparse
import os
import sys
import textwrap
import transaction
import logging

from debian import arfile, debfile
from pyramid.paster import bootstrap
from sqlalchemy.orm.exc import MultipleResultsFound

from reliquary.models import (
    Channel,
    DBSession,
    DebInfo,
    Index,
    Relic,
)


logger = logging.getLogger(__name__)


def pregenerate_deb_indices():
    # get a set of channel/index names that contain relics with deb info
    # for each channel/index
    #   - generate arch Packages
    #   - generate arch Packages.gz
    #   - generate arch Packages.bz2
    #   - generate arch Release
    #   - generate component Release
    pass


def index_deb_info(name, path, obj, indexname):
    # relative to the repository root, which would be something
    # like /api/v1/{channel}/
    filename = "pool/{}/{}".format(indexname, name)

    # md5, sha1, and sha256 of file
    blocksize = 65536
    md5sum_hasher = hashlib.md5()
    sha1_hasher = hashlib.sha1()
    sha256_hasher = hashlib.sha256()
    sha512_hasher = hashlib.sha512()
    with open(path, 'rb') as fin:
        buf = fin.read(blocksize)
        while len(buf) > 0:
            md5sum_hasher.update(buf)
            sha1_hasher.update(buf)
            sha256_hasher.update(buf)
            sha512_hasher.update(buf)
            buf = fin.read(blocksize)
    md5sum = md5sum_hasher.hexdigest()
    sha1 = sha1_hasher.hexdigest()
    sha256 = sha256_hasher.hexdigest()
    sha512 = sha512_hasher.hexdigest()

    # the rest is ripped out of the .deb file or generated based
    # on the information there.
    deb = debfile.DebFile(path)
    control = deb.control.debcontrol()

    # deb control is dict-like object where key lookups are case-insensitive
    multi_arch = control.get("multi-arch", None)
    package = control.get("package", None)
    source = control.get("source", None)
    version = control.get("version", None)
    section = control.get("section", None)
    priority = control.get("priority", None)
    architecture = control.get("architecture", None)
    essential = control.get("essential", None)
    depends = control.get("depends", None)
    recommends = control.get("recommends", None)
    suggests = control.get("suggests", None)
    enhances = control.get("enhances", None)
    pre_depends = control.get("pre-depends", None)
    installed_size = control.get("installed-size", None)
    maintainer = control.get("maintainer", None)
    description = control.get("description", None)
    description_md5 = control.get("description-md5", None)
    homepage = control.get("homepage", None)
    built_using = control.get("built_using", None)

    # if the description-md5 wasn't specified, comput it!
    # the computed value starts at the second character after the colon in the
    # control file (basically, allowing the 'Header: ' format of the text file)
    # and includes a trailing newline character. The value must be lowercase
    # hex md5.
    if not description_md5:
        if description[-1] == "\n":
            description_md5 = hashlib.md5(description.encode()).hexdigest()
        else:
            description_md5 = hashlib.md5((description+"\n").encode()).hexdigest()

    # missing required fields are a deal breaker for including this package
    # in the index
    msg = name+" skipped for deb info: '{}' not found in control"
    if not package:
        logger.error(msg.format('Package'))
        return
    if not version:
        logger.error(msg.format('Version'))
        return
    if not architecture:
        logger.error(msg.format('Architecture'))
        return
    if not maintainer:
        logger.error(msg.format('Maintainer'))
        return
    if not description:
        logger.error(msg.format('Description'))
        return

    kwargs = dict(
        filename=filename,
        md5sum=md5sum,
        sha1=sha1,
        sha256=sha256,
        sha512=sha512,
        multi_arch=multi_arch,
        package=package,
        source=source,
        version=version,
        section=section,
        priority=priority,
        architecture=architecture,
        essential=essential,
        depends=depends,
        recommends=recommends,
        suggests=suggests,
        enhances=enhances,
        pre_depends=pre_depends,
        installed_size=installed_size,
        maintainer=maintainer,
        description=description,
        description_md5=description_md5,
        homepage=homepage,
        built_using=built_using)

    try:
        debinfo_dbobj = DBSession.query(DebInfo) \
                                 .filter_by(relic_id=obj.uid) \
                                 .one_or_none()
        with transaction.manager:
            if debinfo_dbobj:
                logger.info("Adding deb info for " + name)
                DBSession.query(DebInfo) \
                         .filter_by(uid=debinfo_dbobj.uid) \
                         .update(kwargs)
            else:
                logger.info("Updating deb info for " + name)
                kwargs['relic_id'] = obj.uid
                DBSession.add(DebInfo(**kwargs))
    except MultipleResultsFound:
        logger.error("Apparently there's more than one debinfo object"
                     "associated with '"+obj.name+"'")


def reindex():
    description = """\
    Reindex reliquary storage.
    """
    usage = "usage: %prog config_uri"
    parser = optparse.OptionParser(
        usage=usage,
        description=textwrap.dedent(description)
        )

    options, args = parser.parse_args(sys.argv[1:])
    if not len(args) > 0:
        logger.error('at least the config uri is needed')
        return 2
    config_uri = args[0]
    env = bootstrap(config_uri)
    settings, closer = env['registry'].settings, env['closer']
    try:
        # mark everything as dirty so we can delete anything that
        # is not clean by the end of the reindex
        with transaction.manager:
            DBSession.query(Channel).update({'dirty': True})
            DBSession.query(Index).update({'dirty': True})
            DBSession.query(Relic).update({'dirty': True})

        # now, walk through the reliquary and index relics
        reliquary = settings.get('reliquary.location', None)
        # ### CHANNEL
        for channel in os.listdir(reliquary):
            # make sure the directory exists
            channel_path = os.path.join(reliquary, channel)
            if not os.path.isdir(channel_path):
                continue
            # make sure the db object exists
            channel_dbobj = DBSession.query(Channel) \
                                     .filter_by(name=channel) \
                                     .first()
            if not channel_dbobj:
                channel_dbobj = Channel(dirty=False, name=channel)
                with transaction.manager:
                    DBSession.add(channel_dbobj)
            else:
                # channel is has real path and db entry, so should not be dirty
                with transaction.manager:
                    DBSession.query(Channel) \
                             .filter_by(uid=channel_dbobj.uid) \
                             .update({'dirty': False})

            # ### INDEX
            for index in os.listdir(channel_path):
                # make sure the directory exists
                index_path = os.path.join(channel_path, index)
                if not os.path.isdir(index_path):
                    continue
                # make sure the db object exists
                index_dbobj = DBSession.query(Index) \
                                       .filter_by(channel_id=channel_dbobj.uid, name=index) \
                                       .first()
                if not index_dbobj:
                    index_dbobj = Index(dirty=False,
                                        name=index,
                                        channel_id=channel_dbobj.uid)
                    with transaction.manager:
                        DBSession.add(index_dbobj)
                else:
                    # index has real path and db entry, so should not be dirty
                    with transaction.manager:
                        DBSession.query(Index).filter_by(uid=index_dbobj.uid) \
                                 .update({'dirty': False})

                # ### RELIC
                for relic in os.listdir(index_path):
                    relic_path = os.path.join(index_path, relic)
                    try:
                        relic_dbobj = DBSession.query(Relic) \
                                               .filter_by(index_id=index_dbobj.uid, name=relic) \
                                               .one_or_none()
                        relic_mtime = str(os.path.getmtime(relic_path))
                        relic_size = os.path.getsize(relic_path)
                        if relic_dbobj:
                            with transaction.manager:
                                DBSession.query(Relic) \
                                         .filter_by(uid=relic_dbobj.uid) \
                                         .update({'dirty': False,
                                                  'mtime': relic_mtime,
                                                  'size': relic_size})
                        else:
                            relic_dbobj = Relic(dirty=False,
                                                index_id=index_dbobj.uid,
                                                name=relic,
                                                mtime=relic_mtime,
                                                size=relic_size)
                            with transaction.manager:
                                DBSession.add(relic_dbobj)

                        # if the relic is a debian archive, there's additional
                        # info that should be pulled out to make generating
                        # a deb repo more efficient
                        if relic[-4:] == ".deb":
                            index_deb_info(relic, relic_path, relic_dbobj, index)
                    except MultipleResultsFound:
                        logger.error('index [{}/{}/{}] contains non-unique '
                                     '/channel/index/relic_name'
                                     .format(channel, index, relic))

        # delete all relics, still dirty, from the index
        with transaction.manager:
            DBSession.query(Channel) \
                     .filter_by(dirty=True) \
                     .delete()
            DBSession.query(Index) \
                     .filter_by(dirty=True) \
                     .delete()
            DBSession.query(Relic) \
                     .filter_by(dirty=True) \
                     .delete(synchronize_session=False)

        pregenerate_deb_indices()
    except Exception as ex:
        logger.critical("something went wrong")
        logger.critical(ex)
    finally:
        closer()
