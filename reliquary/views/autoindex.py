import time

from pyramid.response import Response
from pyramid.view import view_config

from reliquary.models import DBSession, Relic


@view_config(
    route_name='autoindex',
    renderer='templates/autoindex.pt',
    request_method='GET',
    permission='view')
def autoindex(req):
    channel = req.matchdict.get('channel', 'default')
    index = req.matchdict.get('index', 'default')

    relics = DBSession.query(Relic).filter_by(channel=channel, index=index)
    if relics.count() <= 0:
        return Response('{"status":"error","/channel/index not found"}',
                        content_type='application/json',
                        status_code=404)
    relicout = []
    for relic in relics:
        relic_url = req.route_url('get_relic',
                                  channel=channel,
                                  index=index,
                                  relic_name=relic.name)
        relicout.append(
            '<a href="{}">{}</a>{}{}'.format(
                relic_url,
                relic.name,
                time.strftime('%d-%b-%Y %H:%M', time.gmtime(float(relic.mtime))).rjust(79-len(relic.name), ' '),  # noqa
                str(relic.size).rjust(20, ' ')))

    return dict(display_path='/autoindex/{}/{}'.format(channel, index),
                relics=relicout)
