"""
A custom logger for the MAH application. This was implemented to be easily
used by all parts of the mah package, without having to pass around the
flask.app.logger object and to seperate the log formatting and
configuration features.

Usually, this will be used like so::

    from mah.log import log

    log.debug("This is a debugging message")
"""
import logging
from logging.handlers import SysLogHandler
from logging import FileHandler, getLogger

LEVELS = {
    'DEBUG': logging.DEBUG,
    '10': logging.DEBUG,
    'INFO': logging.INFO,
    '20': logging.INFO,
    'WARNING': logging.WARNING,
    '30': logging.WARNING,
    'ERROR': logging.ERROR,
    '40': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
    '50': logging.CRITICAL
}

#: This instance is imported and used in various places in MAH.
log = getLogger(__name__)
# set this to the lowest level to allow handlers to individually override it.
log.setLevel(logging.DEBUG)

def init(config):
    """
    Initialise the logging system.

    :param config: the logging subsection of the core configuration object,
                   also available as **mah.config.config.logging**. See the
                   :doc:`configuration` section for details.
    """
    global log
    if config.file_level != 'NONE':
        file_handler = FileHandler(config.file_name)
        file_handler.setLevel(LEVELS[config.file_level])
        file_formatter = logging.Formatter(config.file_format)
        file_handler.setFormatter(file_formatter)
        log.addHandler(file_handler)
    if config.syslog_level != 'NONE':
        syslog_handler = SysLogHandler(
            config.syslog_host,
            config.syslog_port,
            config.syslog_facility
        )
        syslog_handler.setLevel(LEVELS[config.syslog_level])
        syslog_formatter = logging.Formatter(config.syslog_format)
        syslog_handler.setFormatter(syslog_formatter)
        log.addHandler(syslog_handler)
