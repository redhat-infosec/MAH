#!/usr/bin/env python
"""
This file contains the flask app object and describes the main entry points
to the web application and maps these to urls.
"""
from datetime import datetime, timedelta
from distutils.version import LooseVersion as Version
import traceback
import flask
from flask import Flask, make_response, render_template
from flask_seasurf import SeaSurf
from mah.config import config
from mah.database import database as db
from mah.log import log

class MAH(Flask):
    """
    MAH-specific Flask object. Installs the SeaSurf instance under the csrf
    attribute, and initialises configuration and logging.
    """
    def __init__(self, *args, **kwargs):
        Flask.__init__(self, *args, **kwargs)
        self.unauthenticated_routes = {'static': True}
        self.csrf = SeaSurf(self)
        if not config.ok:
            log.error("Configuration is not correctly set. Please correct it")
            self.secret_key = "NOT THE REAL SECRET KEY"
            return
        self.config.update(
            SECRET_KEY=config.application.session_key,
            SESSION_COOKIE_SECURE=config.application.session_cookie_secure,
            SESSION_COOKIE_HTTPONLY=config.application.session_cookie_httponly
        )
        # PREFERRED_URL_SCHEME only valid in flask 0.9+
        if Version(flask.__version__) >= Version('0.9'):
            self.config.update(
                PREFERRED_URL_SCHEME=config.application.preferred_url_scheme
            )
        self.secret_key = config.application.session_key # Do we need this?
        # MAH has it's own logging mechanism, and this should be used for flask
        # extensions (such as seasurf)
        for handler in log.handlers:
            self.logger.addHandler(handler) # pylint: disable=E1101

    def route(self, rule, **options):
        """
        Modified route decorator that wraps all routes in an error handling
        routing to centralise logging and error handling.
        """
        def decorator(f):
            def wrap(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                except Exception:
                    log.error(
                        "Unhandled exception in mah.{name}(). {exc}".format(
                            name=f.__name__,
                            exc=traceback.format_exc()
                        )
                    )
                    db.done(False)
                    if self.debug: raise
                    return make_response(render_template('error.html'), 500)
            options['endpoint'] = options.get('endpoint', f.__name__)
            return Flask.route(self, rule, **options)(wrap)
        return decorator

    def unauthenticated_route(self, rule, **options):
        """
        Special route decorator that marks this route as unauthenticated.
        Handlers for these routes must be public, or handle authentication
        checks themselves.
        """
        def decorator(f):
            self.unauthenticated_routes[
                options.get('endpoint', f.__name__)
            ] = True
            return self.route(rule, **options)(f)
        return decorator

app = MAH(__name__)
if not config.ok:
    import mah.routes.error
else:
    import mah.routes.ready

if __name__ == '__main__':
    app.debug = True
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_HTTPONLY=True
    )
    app.run(
        host=config.application.host,
        port=config.application.port
    )
