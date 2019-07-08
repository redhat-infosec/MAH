"""
A debugging authentication method that doesn't use any form of password - just
a username
"""
from flask import flash
from mah.log import log
from mah.authentication import Authentication as AuthBase

class Authentication(AuthBase):
    @classmethod
    def init(cls, config, src):
        """
        Removes the 'password' input as it is not required.
        """
        super(Authentication, cls).init(config, src)
        del cls.inputs['password']

    @classmethod
    def authenticate(cls, form):
        """
        Always succeeds, and logs a 'fake' authentication.
        """
        username = unicode(form['username'].split('@', 1)[0].strip())
        if username == u'':
            flash('{field} is required.'.format(
                field=cls.inputs['username']['label']
            ))
            return None, False # Still need a username, even if no password
        log.warn(u"Authenticating {user} with no password check".format(
            user=username
        ))
        return username, True

    @staticmethod
    def for_production():
        """
        This authentication method is NOT for production use.
        """
        return False
