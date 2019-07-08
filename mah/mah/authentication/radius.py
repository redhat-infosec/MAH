"""
A simple wrapper around the pyrad API to talk to radius authentication servers.
"""
import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary
from flask import flash
from mah.log import log
from mah.authentication import Authentication as AuthBase
from traceback import format_exc

class Authentication(AuthBase):
    @classmethod
    def init(cls, config, src):
        """
        Expects the following configuration variables set:

        radius_server
            The host or IP of the radius server to authenticate against.
        radius_secret
            The secret for connecting to the radius server
        radius_dictionary
            The attribute dictionary
        radius_nas_identifier
            The NAS identifier attribute
        radius_nas_ip_address
            The IP address attribute
        """
        config.radius_server = src.str('radius_server')
        config.radius_secret = src.str('radius_secret')
        config.radius_dictionary = src.str('radius_dictionary')
        config.radius_nas_identifier = src.str('radius_nas_identifier')
        config.radius_nas_ip_address = src.str('radius_nas_ip_address')
        super(Authentication, cls).init(config, src)

    @classmethod
    def authenticate(cls, form):
        """
        Authenticates to the configured RADIUS server.
        """
        try:
            username = unicode(form['username'].split('@', 1)[0].strip())
        except Exception:
            flash("{field} is required.".format(
                field=cls.inputs['username']['label']
            ))
            log.error("Username field missing from authentication form!")
            return None, False
        try:
            password = unicode(form['password'])
        except Exception:
            flash("{field} is required.".format(
                field=cls.inputs['password']['label']
            ))
            log.error("Password field missing from authentication form!")
            return username, False
        srv = Client(
            server=cls.config.radius_server,
            secret=cls.config.radius_secret,
            dict=Dictionary(dict=cls.config.radius_dictionary)
        )
        req = srv.CreateAuthPacket(code=pyrad.packet.AccessRequest)
        req["User-Name"] = username
        req["User-Password"] = req.PwCrypt(password)
        req["NAS-Identifier"] = cls.config.radius_nas_identifier
        # The IP address config option could be made optional
        # and determined from radius_nas_identifier
        req["NAS-IP-Address"] = cls.config.radius_nas_ip_address
        log.debug(
            "Attempting radius auth: Server: {server}; User-Name: {user}; "
            "NAS-Identifier {nasid}; NAS-IP: {nasip}; Dictionary {dict}".format(
                server=srv.server,
                user=req["User-Name"],
                nasid=req["NAS-Identifier"],
                nasip=req["NAS-IP-Address"],
                dict=cls.config.radius_dictionary
            )
        )
        try:
            reply = srv.SendPacket(req)
        except pyrad.client.Timeout:
            flash('An error has occurred. Please try again.')
            log.error(
                "Connection to radius server timed out. This may "
                "be caused by incorrect sever settings. Check the radius "
                "server logs for more information. {err}".format(
                    err=format_exc()
                )
            )
            return username, False
        except Exception:
            flash('An error has occurred. Please try again.')
            log.error("Radius server connect failed. {err}".format(
                err=format_exc()
            ))
            return username, False
        return username, reply.code == pyrad.packet.AccessAccept
