from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPNotFound
from pyramid.security import ALL_PERMISSIONS, Allow, Authenticated, Everyone
from sqlalchemy import engine_from_config

from reliquary.models import DBSession, Base


# helper for auto-appending slashes to not found urls
def notfound(req):
    return HTTPNotFound()


def groupfinder(username, password, req):
    items = req.registry.settings.get('reliquary.auth', '').split()
    for item in items:
        userparts = item.split(':')
        namepart = userparts[0]
        keypart = userparts[1]
        grouppart = []
        if len(userparts) > 2:
            grouppart = userparts[2].split(',')
        if namepart.lower().strip() == username.lower().strip() \
                and keypart == password:
            return grouppart
    return None


class Root(object):
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, Authenticated, 'put'),
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, req):
        self.request = req


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    authn_policy = BasicAuthAuthenticationPolicy(
        groupfinder,
        realm=settings['reliquary.realm'],
        debug=settings['pyramid.debug'])
    authz_policy = ACLAuthorizationPolicy()

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(
        settings=settings,
        authentication_policy=authn_policy,
        authorization_policy=authz_policy,
        root_factory=Root,
    )

    config.include('pyramid_chameleon')

    #config.add_static_view('static', 'static', cache_max_age=3600)

    # ui
    config.add_route('home', '/api/v1/', request_method='GET')

    # basic api
    config.add_route('put_relic', '/api/v1/raw/{channel}/{index}/{relic_name}', request_method='PUT')
    config.add_route('get_relic', '/api/v1/raw/{channel}/{index}/{relic_name}', request_method='GET')

    # autoindex (nginx autogenerate index page compatible)
    config.add_route('autoindex', '/api/v1/autoindex/{channel}/{index}/', request_method='GET')

    # python package index (PEP-503 compliant)
    # PROXY
    config.add_route('pypi_proxy_simple_package', '/api/v1/python/proxy/{channel}/{index}/simple/{package}/', request_method='GET')
    config.add_route('pypi_proxy_simple', '/api/v1/python/proxy/{channel}/{index}/simple/', request_method='GET')
    # just to keep compat with pypi.python.org package locations -- calls out
    # to upstream or to get_relic route
    config.add_route('pypi_proxy_package', '/api/v1/python/proxy/{channel}/{index}/packages/{parta}/{partb}/{hash}/{package}', request_method='GET')
    # SELF-HOSTED
    config.add_route('pypi_simple_package', '/api/v1/python/{channel}/{index}/simple/{package}/', request_method='GET')
    config.add_route('pypi_simple', '/api/v1/python/{channel}/{index}/simple/', request_method='GET')

    # commonjs registry (http://wiki.commonjs.org/wiki/Packages/Registry)
    # npmjs.org is historically based on this, and npm should be compatible
    # PROXY
    # these mostly try to replicate the npmjs registry public api in function
    # npmjs registry api: https://github.com/npm/registry/blob/master/docs/REGISTRY-API.md
    # set the registry used with npm-config (.npmrc files): https://docs.npmjs.com/files/npmrc
    # http://registry.npmjs.org/<name>/<version>
    config.add_route('commonjs_proxy_registry_package_version', '/api/v1/commonjs/proxy/{channel}/{index}/{package}/{version}/', request_method='GET')
    # http://registry.npmjs.org/<name>/
    config.add_route('commonjs_proxy_registry_package_root', '/api/v1/commonjs/proxy/{channel}/{index}/{package}/', request_method='GET')
    # http://registry.npmjs.org/-/all
    config.add_route('commonjs_proxy_registry_root', '/api/v1/commonjs/proxy/{channel}/{index}/', request_method='GET')
    # http://registry.npmjs.org/-/<package>-<version>.tgz
    config.add_route('commonjs_proxy_package', '/api/v1/commonjs/proxy/package/{channel}/{index}/{package}/{version}', request_method='GET')
    # SELF HOSTED
    config.add_route('commonjs_registry_root', '/api/v1/commonjs/{channel}/{index}/', request_method='GET')
    config.add_route('commonjs_registry_package_root', '/api/v1/commonjs/{channel}/{index}/{package}/', request_method='GET')
    config.add_route('commonjs_registry_package_version', '/api/v1/commonjs/{channel}/{index}/{package}/{version}/', request_method='GET')

    # debian repository (https://wiki.debian.org/RepositoryFormat)
    #   additional info: http://www.ibiblio.org/gferg/ldp/giles/repository/repository-2.html
    # these are the minimum required paths
    # example sources.list entry: deb http://127.0.0.1/api/v1/debian/wildcard trusty main
    config.add_route('debian_distrelease', '/api/v1/debian/{channel}/dist/{index}/Release', request_method='GET')                                   #
    config.add_route('debian_archrelease', '/api/v1/debian/{channel}/dist/{index}/main/binary-{arch}/Release', request_method='GET')                #
    config.add_route('debian_archpackages', '/api/v1/debian/{channel}/dist/{index}/main/binary-{arch}/Packages', request_method='GET')              # x
    config.add_route('debian_archpackagesgz', '/api/v1/debian/{channel}/dist/{index}/main/binary-{arch}/Packages.gz', request_method='GET')         # x
    config.add_route('debian_archpackagesbz2', '/api/v1/debian/{channel}/dist/{index}/main/binary-{arch}/Packages.bz2', request_method='GET')       # x
    config.add_route('debian_poolpackage', '/api/v1/debian/{channel}/pool/{index}/{relic_name}', request_method='GET')                              # x
    # additional paths that could be just a directory listing of some sort (like autoindex)
    config.add_route('debian_archindex', '/api/v1/debian/{channel}/dist/{index}/main/binary-{arch}/', request_method='GET')                         # x
    config.add_route('debian_compindex', '/api/v1/debian/{channel}/dist/{index}/main/', request_method='GET')                                       # x
    config.add_route('debian_distindex', '/api/v1/debian/{channel}/dist/{index}/', request_method='GET')                                            # x
    config.add_route('debian_distrootindex', '/api/v1/debian/{channel}/dist/', request_method='GET')                                                # x
    config.add_route('debian_channelindex', '/api/v1/debian/{channel}/', request_method='GET')                                                      # x
    config.add_route('debian_pooldistindex', '/api/v1/debian/{channel}/pool/{index}/', request_method='GET')                                        # x
    config.add_route('debian_poolrootindex', '/api/v1/debian/{channel}/pool/', request_method='GET')                                                # x

    config.add_notfound_view(notfound, append_slash=True)

    config.scan('.views')

    return config.make_wsgi_app()
