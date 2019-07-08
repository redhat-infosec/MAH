"""
Use LDAP or AD for directory services.
"""
import ldap3, traceback
try:
    from urlparse import urlparse
except:
    from urllib.parse import urlparse
from mah.directory import Directory as DirectoryBase, Person as PersonBase
from mah.log import log

class Person(PersonBase):
    """
    Ensure all requested attributes are listed, even if they are set to None
    """
    def __init__(self, data, attributes):
        super(Person, self).__init__(
            [data.get(attr, None) for attr in attributes]
        )

class Directory(DirectoryBase):
    """
    """
    def __init__(self):
        self.connected = False
        self._connect()

    def _connect(self):
        if self.connected:
            return
        self.server = ldap3.Server(
            host=self.config.ldap_hostname,
            port=self.config.ldap_port,
            use_ssl=self.config.ldap_use_ssl
        )
        self.conn = ldap3.Connection(
            self.server,
            auto_bind=False,
            user=self.config.ldap_username,
            password=self.config.ldap_password,
            lazy=False,
            read_only=True
        )
        try:
            self.conn.bind()
        except Exception:
            log.error("Could not bind to LDAP server: {err}".format(
                err=traceback.format_exc()
            ))
        else:
            self.connected = True

    def _search(self, search=None):
        if not self.connected:
            return []
        cookie = None
        ret = []
        log.debug("Running search {search}".format(search=search))
        while True:
            self.conn.search(
                search_base=self.config.ldap_base,
                search_filter=search,
                search_scope=ldap3.SUBTREE,
                attributes=self.config.attributes,
                paged_size=self.config.ldap_paged_size,
                paged_cookie=cookie,
                size_limit=self.config.ldap_size_limit,
                time_limit=self.config.ldap_time_limit
            )
            ret.extend([self._clean(entry) for entry in self.conn.entries])
            if len(ret) >= self.config.ldap_size_limit:
                return ret[:self.config.ldap_size_limit]
            cookie = self._page_cookie()
            if cookie == '':
                return ret

    @classmethod
    def init(cls, config, src):
        """
        Expects the following configuration variables set:

        **ldap_filter**
            Fields to compare search strings against. Defaults to ['uid', 'cn']
        **ldap_size_limit**
            Maximum number of search results to return. Defaults to 250.
        **ldap_paged_size**
            Maximum number of search results per page. Defaults to None, which
            turns off paging.
        **ldap_time_limit**
            Maximum number of seconds a search should run for. Defaults to 15.
        **ldap_url**
            LDAP connection URL of the form
            **SCHEME**://**USER**:**PASS** @ **HOST**:**PORT**/**BASE**

            * If **SCHEME** is ldaps, SSL will be used.
            * **USER** and **PASS** are optional, and will be used as
              credentials.
            * **HOST** is the LDAP or AD host to connect to.
            * **PORT** is the port that the LDAP or AD service is listening on.
              By default this is 389
            * **BASE** is the LDAP search base, something akin to 
              *ou=users,dc=corp,dc=com*
        """
        super(Directory, cls).init(config, src)
        config.ldap_filter = src.strlist('ldap_filter', ['uid', 'cn'])
        config.ldap_size_limit = src.int('ldap_size_limit', 250)
        config.ldap_paged_size = src.int('ldap_paged_size', None)
        config.ldap_time_limit = src.int('ldap_time_limit', 15)
        config.ldap_url = src.str('ldap_url')
        url = urlparse(config.ldap_url)
        config.ldap_hostname = url.hostname
        config.ldap_port = 389 if url.port is None else url.port
        config.ldap_base = url.path[1:]
        config.ldap_username = url.username
        config.ldap_password = url.password
        config.ldap_use_ssl = url.scheme == 'ldaps'

    def search(self, query):
        """
        Search the LDAP or AD directory, comparing against the fields listed in
        mah.config.config.directory.ldap_filter.
        """
        query = u'(|{query})'.format(
            query=u''.join([
                u'({attr}=*{query}*)'.format(
                    attr=attr,
                    query=query
                ) for attr in self.config.ldap_filter
            ])
        ).encode('ascii', 'ignore')
        results = self._search(query)
        results.sort()
        return [Person(result, self.config.attributes) for result in results]

    def user(self, uid):
        """
        Find a specific user in the LDAP/AD directory.
        """
        search=u'({attr}=*{uid}*)'.format(
            attr=self.config.id_attribute,
            uid=uid
        )
        results = self._search(search)
        if len(results) == 1:
            return Person(results[0], self.config.attributes)
        if len(results) != 0:
		    # a search for a (non-wild carded) user id returned something
            # other than 0 or 1 results.
            log.error(
                "ldap error: searching for a uid of {uid} without wildcards "
                "returned {results} results. Possible LDAP "
                "inconsistency?".format(uid=uid, results=len(results))
            )
        return None

    def _clean(self, entry):
        return {
            key: entry[key].value for key in entry.entry_attributes
        }

    def _page_cookie(self):
        try:
            cookie = self.conn.result['controls']['1.2.840.113556.1.4.319']
            return cookie['value']['cookie']
        except Exception:
            return ''
