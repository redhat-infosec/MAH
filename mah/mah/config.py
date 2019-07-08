"""
A simple, shared configuration configuration object based on the standard
python `ConfigParser <http://docs.python.org/library/configparser.html>`_.

**config**
    Global configuration object. Can be treated as a dictionary with
    case-insensitive keys, or as an object with attributes that correspond to
    configuration sections. For instance, the following are equivalent::

        config['Application']
        config['application']
        config.application
        config.Application

    The value of which can be another configuration object or a string, boolean,
    integer, or float value, or a list of strings, booleans, integers or floats.

    See the :doc:`configuration` section for details.
"""
from ConfigParser import (
    RawConfigParser as ConfigParserBase,
    NoOptionError, NoSectionError
)
from traceback import format_exc
import os, re, importlib
import mah.log
from mah.database import database as db

_valid_name = re.compile(r'^[A-Za-z][A-Za-z0-9_]*\Z')

_NO_DEFAULT = object()

class ConfigParser(ConfigParserBase):
    def getint(self, section, option, default=_NO_DEFAULT):
        try:
            return ConfigParserBase.getint(self, section, option)
        except (NoSectionError, NoOptionError):
            # Missing is OK if we have a default to fall back to
            if default is _NO_DEFAULT: raise
            return default

    def getboolean(self, section, option, default=_NO_DEFAULT):
        try:
            return ConfigParserBase.getboolean(self, section, option)
        except (NoSectionError, NoOptionError):
            if default is _NO_DEFAULT: raise
            return default

    def getfloat(self, section, option, default=_NO_DEFAULT):
        try:
            return ConfigParserBase.getfloat(self, section, option)
        except (NoSectionError, NoOptionError):
            if default is _NO_DEFAULT: raise
            return default

    def get(self, section, option, default=_NO_DEFAULT):
        try:
            return ConfigParserBase.get(self, section, option)
        except (NoSectionError, NoOptionError):
            if default is _NO_DEFAULT: raise
            return default

    def section(self, name):
        return ConfigSection(self, name)

class ConfigSection(object):
    def __init__(self, cfg, name):
        self._cfg = cfg
        self.name = name

    def _list(self, option, default, cast):
        raw = self._cfg.get(self.name, option, default)
        if raw is default: return raw
        return [cast(x.strip()) for x in raw.split(',')]

    def _castint(self, raw):
        return int(raw, 10)

    def _castfloat(self, raw):
        return float(raw)

    def _castbool(self, raw):
        chk = raw.lower()
        if chk in ('true', 'on', 'yes', '1'): return True
        if chk in ('false', 'off', 'no', '0'): return False
        raise ValueError('Not a boolean: {raw}'.format(raw=raw))

    def _caststr(self, raw):
        return raw

    def int(self, option, default=_NO_DEFAULT):
        return self._cfg.getint(self.name, option, default)

    def intlist(self, option, default=_NO_DEFAULT):
        return self._list(option, default, self._castint)

    def float(self, option, default=_NO_DEFAULT):
        return self._cfg.getfloat(self.name, option, default)

    def floatlist(self, option, default=_NO_DEFAULT):
        return self._list(option, default, self._castfloat)

    def bool(self, option, default=_NO_DEFAULT):
        return self._cfg.getboolean(self.name, option, default)

    def boollist(self, option, default=_NO_DEFAULT):
        return self._list(option, default, self._castbool)

    def str(self, option, default=_NO_DEFAULT):
        return self._cfg.get(self.name, option, default)

    def strlist(self, option, default=_NO_DEFAULT):
        return self._list(option, default, self._caststr)

class AttribDict(dict):
    def __getattr__(self, key):
        lkey = key.lower()
        if lkey in self.keys():
            return self[lkey]
        raise AttributeError(
            "{cls!r} object has no attribute {attr!r}".format(
                cls=self.__class__,
                attr=key
            )
        )

    def __setattr__(self, key, value):
        if key[0] == '_':
            super(AttribDict, self).__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(AttribDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(AttribDict, self).__getitem__(key.lower())

    def get(self, key, default=None):
        return super(AttribDict, self).get(key.lower(), default)

    def has_key(self, key):
        return super(AttribDict, self).has_key(key.lower())

def load_module(config, src, parent, cfgparent, clsname, ifaces):
    if not _valid_name.match(config.type):
        raise ValueError(
            'Config {parent}.type must contain only alphanumerics and '
            'underscores, and must start with an alphabetic character'.format(
                parent=cfgparent
            )
        )
    try:
        config.module = importlib.import_module(
            'mah.{parent}.{pkg}'.format(parent=parent, pkg=config.type)
        )
    except Exception:
        raise RuntimeError(
            'Failed to import mah.{parent}.{pkg} - {trace}'.format(
                parent=parent,
                pkg=config.type,
                trace=format_exc()
            )
        )
    cls = getattr(config.module, clsname)
    try:
        cls.init(config, src)
    except Exception:
        raise RuntimeError(
            'Failed to initialise mah.{parent}.'
            '{pkg}.{cls} - {trace}'.format(
                parent=parent,
                pkg=config.type,
                cls=clsname,
                trace=format_exc()
            )
    )
    for iface in ifaces:
        if not callable(getattr(cls, iface, None)):
            raise RuntimeError(
                'mah.{parent}.{pkg}.{cls} is invalid - missing '
                'required interface method {method}'.format(
                    parent=parent,
                    pkg=config.type,
                    cls=clsname,
                    method=iface
                )
            )

class Config(AttribDict):
    def __init__(self, src=None):
        if src is None: return
        # We're the main config. Set ourselves up
        self.ok = False

        # Logging section
        # Do this section first and set up logging as fast as we can - even
        # before mah.config itself is set up. To do this, we pass the logging
        # section of the config to mah.log.init() so it doesn't have to wait.
        # We'll even delay raising an error until the very last second in case
        # at least one logging method is valid.

        # Note that if the configuration is unparseable, or if the logging
        # section has errors, logs might be unavailable or not where you're
        # expecting them.
        section = Config()
        rsection = src.section('logging')
        section.file_level = rsection.str('file_level', 'DEBUG')
        errors = []
        if section.file_level != 'NONE':
            if section.file_level in mah.log.LEVELS:
                section.file_name = rsection.str('file_name')
                section.file_format = rsection.str(
                    'file_format',
                    '%(asctime)s %(name)s(%(threadName)s) '
                    '%(levelname)s: %(msg)s'
                )
            else:
                errors.append('logging.file_level')
        section.syslog_level = rsection.str('syslog_level', 'DEBUG')
        if section.syslog_level != 'NONE':
            if section.syslog_level in mah.log.LEVELS:
                section.syslog_host = rsection.str('syslog_host', 'localhost')
                section.syslog_port = rsection.int('syslog_port', 514)
                section.syslog_facility = rsection.str(
                    'syslog_facility', 'user'
                )
                section.syslog_format = rsection.str(
                    'syslog_format', '%(name)s: %(msg)s'
                )
            else:
                errors.append('logging.syslog_level')
        self.logging = section
        if len(errors) < 2:
            mah.log.init(self.logging)
        if len(errors):
            raise ValueError(
                'Config {config} is invalid'
                ' - must be one of {options}'.format(
                    config=', '.join(errors),
                    options='NONE, ' + ', '.join(mah.log.LEVELS)
                ))

        # Application section
        section = Config()
        rsection = src.section('application')
        section.host = rsection.str('host')
        section.port = rsection.int('port')
        section.session_key = rsection.str('session_key')
        section.session_timeout = rsection.int('session_timeout', 600)
        section.session_cookie_secure = rsection.bool(
            'session_cookie_secure', True
        )
        section.session_cookie_httponly = rsection.bool(
            'session_cookie_httponly', True
        )
        section.preferred_url_scheme = rsection.str(
            'preferred_url_scheme', 'https'
        )
        section.refresh = rsection.int('refresh', 30)

        if section.session_timeout < 30:
            raise ValueError(
                'Config application.session_timeout must be at least 30'
            )
        if section.refresh < 10:
            raise ValueError('Config application.refresh must be at least 10')
        self.application = section

        # Authentication section
        section = Config()
        rsection = src.section('authentication')
        section.timeout = rsection.int('timeout', 300)
        section.length = rsection.int('length', 8)
        section.variable_length = rsection.bool('variable_length', True)
        if section.length < 5 or section.length > 128:
            raise ValueError(
                'Config authentication.length must be '
                'between 5 and 128 inclusive'
            )
        self.authentication = section

        # Database section
        section = Config()
        rsection = src.section('database')
        section.connect = rsection.str('connect')
        section.logsql = rsection.bool('logsql', False)
        self.database = section

        # Login section
        section = Config()
        rsection = src.section('login')
        section.type = rsection.str('type', 'none')
        load_module(
            section, rsection, 'authentication', 'login', 'Authentication',
            ('authenticate', 'for_production')
        )
        auth = section.module.Authentication
        if (not callable(getattr(auth, 'authenticate', None)) or
            not callable(getattr(auth, 'for_production', None))):
            raise RuntimeError(
                'mah.authentication.{pkg} is invalid - '
                'missing required interface'.format(
                    pkg=section.type
                )
            )
        self.login = section

        # Directory section
        section = Config()
        rsection = src.section('directory')
        section.attributes = src.strlist('attributes')
        if len(section.attributes) < 2:
            raise ValueError(
                'Config directory.attributes should '
                'be a list of at least two entries'
            )
        section.attribute_names = src.strlist('attribute_names')
        if len(section.attribute_names) < 2:
            raise ValueError(
                'Config directory.attribute_names should '
                'be a list of at least two entries'
            )
        if len(section.attribute_names) != len(section.attributes):
            raise ValueError(
                'Config directory.attribute_names should be of '
                'the same length as directory.attributes'
            )
        section.id_attribute = src.str('id_attribute')
        if section.id_attribute != section.attributes[0]:
            raise ValueError(
                'Config directory.id_attribute should '
                'match first entry of directory.attributes'
            )
        section.name_attribute = src.str('name_attribute')
        if section.name_attribute != section.attributes[1]:
            raise ValueError(
                'Config directory.name_attribute should '
                'match second entry of directory.attributes'
            )
        section.type = rsection.str('type')
        load_module(
            section, rsection, 'directory', 'directory', 'Directory',
            ('search', 'user')
        )
        self.directory = section

        # Report section
        section = Config()
        rsection = src.section('report')
        section.email_from = rsection.str('email_from', 'mah@corp.com')
        section.email_to = rsection.strlist('email_to', ['mah@corp.com'])
        section.subject = rsection.str(
            'subject', 'MAH suspicious activity report'
        )
        section.smtp_server = rsection.str('smtp_server', 'localhost')
        self.report = section
        self.ok = True

#: The config object. This is imported directly and used in various places in
#: MAH.
config = Config()
config.ok = False
config.error = 'Config not loaded.'

def load():
    global config
    src = os.environ.get('MAHCONFIG', 'mah.conf')
    raw = ConfigParser()
    try:
        with open(src, 'r') as cfg:
            raw.readfp(cfg)
    except Exception as e:
        config.error = 'Failed to open or read configuration file'
        config.exception = e
        config.trace = format_exc()
        return
    try:
        config = Config(raw)
    except Exception as e:
        config.error = 'Configuration error detected'
        config.exception = e
        config.trace = format_exc()
    try:
        db.init()
    except Exception as e:
        config.ok = False
        config.error = (
            'Database initialisation failed - configuration incorrect?'
        )
        config.exception = e
        config.trace = format_exc()
load()    
del load, load_module
