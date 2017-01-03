import optparse
import os
import sys
import textwrap
import transaction

from pyramid.paster import bootstrap

from reliquary.models import DBSession, Relic


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
        print('at least the config uri is needed')
        return 2
    config_uri = args[0]
    env = bootstrap(config_uri)
    settings, closer = env['registry'].settings, env['closer']
    try:
        # mark everything as dirty so we can delete anything that
        # is not clean by the end of the reindex
        with transaction.manager:
            DBSession.query(Relic).update({'dirty': True})

        # now, walk through the reliquary and index relics
        reliquary = settings.get('reliquary.location', None)
        for channel in os.listdir(reliquary):
            channel_path = os.path.join(reliquary, channel)
            if not os.path.isdir(channel_path):
                continue
            for index in os.listdir(channel_path):
                index_path = os.path.join(channel_path, index)
                if not os.path.isdir(index_path):
                    continue
                for relic in os.listdir(index_path):
                    relic_path = os.path.join(index_path, relic)
                    matching = DBSession.query(Relic).filter_by(channel=channel, index=index, name=relic)  # noqa
                    if matching.count() > 0:
                        # more than one match == not good
                        if matching.count() > 1:
                            print('index contains non unique /channel/index/relic_name')  # noqa
                            return 2
                        with transaction.manager:
                            matching.update({
                                'dirty': False,
                                'mtime': str(os.path.getmtime(relic_path)),
                                'size': os.path.getsize(relic_path)})
                    else:
                        obj = Relic(dirty=False,  # new are not dirty yet :)
                                    channel=channel,
                                    index=index,
                                    name=relic,
                                    mtime=str(os.path.getmtime(relic_path)),
                                    size=os.path.getsize(relic_path))
                        with transaction.manager:
                            DBSession.add(obj)

        # delete all relics, still dirty, from the index
        with transaction.manager:
            DBSession.query(Relic).filter_by(dirty=True).delete(synchronize_session=False)
    finally:
        closer()
