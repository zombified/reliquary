import optparse
import os
import sys
import textwrap
import transaction
import logging

from pyramid.paster import bootstrap
from sqlalchemy.orm.exc import MultipleResultsFound

from reliquary.models import Channel, DBSession, Index, Relic


logger = logging.getLogger(__name__)


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
    finally:
        closer()
