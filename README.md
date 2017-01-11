Reliquary
=========

The key idea of Reliquary is that it should be able to serve an interfance
compatible with existing tools for a repository of packages. Additionally, it
can function as a sort of caching proxy for upstream sources.

In a sense, it is comparible in desired function to
["Binary Repository Manager"](https://binary-repositories-comparison.github.io/)
services, sometimes referred to as "Software Artifact Repositories."

For example, Python has a [standard](https://www.python.org/dev/peps/pep-0503/)
that is well known and used by tools like _pip_ or _buildout_ to fetch
dependencies. Reliquary provides two implementations of this interface -- one
that acts as a self hosted interface, and another that acts as a caching proxy
to an upstream python package index.

Reliquary is not intended to be limited to _just_ Python packages. CommonJS/NPM,
APT, and any other standardized repository formats are all possible interfaces
for Reliquary to implement.


Current Status
--------------

This project is very much in development, and will likely drastically change
frequently.

Currently implemented are:

  * direct get/put for packages
  * nginx XSendFile compatibility (recommended way of serving file blobs)
  * [PEP-503](https://www.python.org/dev/peps/pep-0503/) compatible interface
  * caching proxy for https://pypi.python.org/
  * [CommonJS Package Registry](http://wiki.commonjs.org/wiki/Packages/Registry) compatible interface
  * caching proxy for https://registry.npmjs.org/
  * debian repository compatible interface (as defined by [the debian wiki](https://wiki.debian.org/RepositoryFormat))

Planned Features for the near future:

  * _configurable_ proxy upstream for python and commonjs end points
  * more work on authentication and authorization (more specific permissions,
    better mechanism for generating and storing basic auth keys, maybe private
    url scheme, maybe ldap integration)
  * debian repository compatible caching proxy
  * a mechanism for requesting a merged set of indices within a channel

Features that may be considered based on feasibility include a YUM and RubyGems
interface. Other interfaces may be possible with interest.
