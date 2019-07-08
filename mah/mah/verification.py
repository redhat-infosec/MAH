# This is the object to relational mapping and class infrastructure to
# represent and authentication from one user of another. Internally these
# are referred to as 'Verifications' to avoid overloading with user
# authentication.

from mah.config import config
from mah.log import log
from mah.database import database as db
from mah.nato import NATO
from sqlalchemy import (
    Table, Column, Integer, String, Boolean, DateTime, Sequence, or_, and_
)
from datetime import datetime, timedelta, time
import os, random, hashlib, binascii

# This package should NEVER be imported without mah.database first being
# initialised, but if it is (for instance, for Sphinx documentation), make a
# dummy version of the db.Base base object.
Base = object if db.Base is None else db.Base

class Verification(Base):
    """
    Represents a one-way authentication between two users. An authentication
    consists of a username/uid of the authenticator (referred to as the
    "source") and the username/uid of the authenticated party (destination).

    This class generates a short, human manageable shared secret and puts a
    short (ideally around 5 - 15 minutes) life span on the authentication.
    The shared secret is a pseudo random hash truncated to a reasonable
    (human memorable) configurable length (default: 6).

    The expiry time is set a configurable number of seconds into the future
    (default 300).

    This could be prone to collisions, but a given a reasonable length of the
    shared secret, a short expiry time and the fact authentication occurs
    between humans it provides a reasonable solution.
    """
    __tablename__ = 'authentications'

    auth_id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    """
    A unique identifer for the authentication. This is never displayed to
    the end user and is automatically incremented as authentications are
    added.
    """
    source_uid = Column(String(32), nullable=False)
    """
    The username/uid of the person who initiated the authentication.
    """
    source_name = Column(String(200), nullable=False)
    """
    The human readable name of the source. This is looked up from the staff
    directory.
    """
    dest_uid = Column(String(32), nullable=False)
    """
    The username/uid of the person who was authenticated.
    """
    dest_name = Column(String(200), nullable=False)
    """
    The human readable name of the source of the authentication. This is
    looked up from the staff directory.
    """
    shared_secret = Column(String(128), nullable=False)
    """
    A short, (relatively) unguessable string represent the shared secret in
    this authentication.
    """
    expiry = Column(DateTime, nullable=False, default=datetime.utcnow())
    """
    The expiry time of this authentication.
    """
    reciprocated = Column(Boolean, nullable=False, default=False)
    """
    A flag to show if the authentication exists in the other direction
    (destination user -> source user). This is primarily used to simplify
    template logic.
    """
    expiry_string = ""
    """
    A user friendly and timezone independent string to represent the time
    before an auth expires. e.g. "20 seconds", "4 minutes". This is used to
    improve usability, by not having users exposed to timezone issues,
    where possible. This is not stored in the database, but instead
    calculated when objects are queried.
    """
    nato_code = ""
    """
    The authentication strings in the phonetic alphabet (NATO) codes. This
    is not stored in the database, but instead generated when objected are
    queried.
    """

    def __init__(self, source_uid, dest_uid):
        """
        Constructs a persistent authentication object, representing a
        one-way authentication: the source user id authenticates the
        destination uid.

        This method also looks up the full name corresponding to each user
        id and generates a shared secret and an expiry time.

        :param source_uid: the user who initiated the authentication
        :param dest_uid: the user who was authenticated.
        """
        self.source_uid = source_uid
        self.dest_uid = dest_uid

        staff = config.directory.module.Directory()
        src = staff.user(source_uid)
        dst = staff.user(dest_uid)
        if src == None:
            message = (
                u"Authentication source ({src}) not found in directory".format(
                    src=source_uid
                )
            )
            log.error(message)
            raise Exception(message)
        elif dst == None:
            message = (
                u"Authentication destination ({dst}) "
                u"not found in directory".format(dst=dest_uid)
            )
            log.error(message)
            raise Exception(message)
        else:
            self.source_name = src.attributes[1]
            self.dest_name = dst.attributes[1]

        reciprocated_auth = self.get(dest_uid, source_uid)
        if reciprocated_auth:
            self.reciprocated = True
            reciprocated_auth.reciprocated = True

        td = timedelta(seconds=config.authentication.timeout)
        self.expiry = datetime.utcnow() + td
        self.expiry_string = self._approx_time_delta(td)
        self.shared_secret = self._gen_shared_secret('{src}{exp}{dst}'.format(
            src=source_uid.decode(),
            exp=self.expiry_string,
            dst=dest_uid.decode
        ))
        self.nato_code = self._nato_code(self.shared_secret)
        log.debug(
            u'New authentication created by {src} to {dst} and '
            u'expiring at {exp}'.format(
                src=source_uid,
                dst=dest_uid,
                exp=self.expiry
            )
        )

    def __repr__(self):
        """
        Return a python-like string representation of the authentication
        object.
        """
        return u"<Authentication('{src}' -> '{dst}' @ '{exp} UTC')>".format(
            src=self.source_uid,
            dst=self.dest_uid,
            exp=self.expiry
        )

    @classmethod
    def get(cls, src_uid, dst_uid):
        """
        Retreive the unexpired authentication object, given a source and a
        destination uid. This function can only ever return 1 or 0 elements.

        :param src_uid: the source user id
        :param dst_uid: the destination user id.
        :rtype: a single authentication object or None.
        """
        results = db.session.query(Verification).filter( # pylint: disable=E1101
            and_(
                Verification.expiry > datetime.utcnow(),
                Verification.source_uid == src_uid,
                Verification.dest_uid == dst_uid
            )
        )
        if results.count() == 0:
            return None
        elif results.count() == 1:
            return cls._expand(results[0])
        else:
            raise Exception('database inconsistency')

    @classmethod
    def by_id(cls, auth_id):
        """
        Retreive the authentication object which matches the unique id.

        :param src_uid: the source user id
        :param dst_uid: the destination user id.
        :rtype: a single authentication object or None.
        """
        results = db.session.query(Verification).filter( # pylint: disable=E1101
            Verification.auth_id == auth_id
        )
        if results.count() == 0:
            return None
        elif results.count() == 1:
            return cls._expand(results[0])
        else:
            raise Exception(u'Database inconsistency - identical auth_ids')

    @classmethod
    def by_src(cls, uid):
        """
        Retrieve non-expired authentication objects with a given source uid.

        :param src_uid: the source user id
        :param dst_uid: the destination user id.
        :rtype: a list of authentication objects or None.
        """
        results = db.session.query(Verification).filter( # pylint: disable=E1101
            and_(
                Verification.expiry > datetime.utcnow(),
                Verification.source_uid == uid
            )
        ).all()
        for result in results:
            cls._expand(result)
        return results

    @classmethod
    def by_dst(cls, uid):
        """
        Retrieve non-expired authentication objects with a given destination uid.

        :param src_uid: the source user id
        :param dst_uid: the destination user id.
        :rtype: a list of authentication objects or None.
        """
        results = db.session.query(Verification).filter( # pylint: disable=E1101
            and_(
                Verification.expiry > datetime.utcnow(),
                Verification.dest_uid == uid
            )
        ).all()
        for result in results:
            cls._expand(result)
        return results

    @classmethod
    def all(cls, uid):
        """
        Retrieve all authentication objects for which the uid matches either
        the source or destination, regardless of expiry time.

        :param src_uid: the source user id
        :param dst_uid: the destination user id.
        :rtype: a list of authentication objects or None.
        """
        results = db.session.query(Verification).filter( # pylint: disable=E1101
            or_(
                Verification.source_uid == uid,
                Verification.dest_uid == uid
            )
        ).all()
        for result in results:
            cls._expand(result)
        return results

    @staticmethod
    def exists(src_uid, dst_uid):
        """
        Given the source and destination of a authentication, check if an
        authentication already exists and if it does, return true.

        :param src_uid: the source user id
        :param dst_uid: the destination user id.
        :rtype: bool
        """
        return db.session.query(Verification).filter( # pylint: disable=E1101
            and_(
                Verification.expiry > datetime.utcnow(),
                Verification.source_uid == src_uid,
                Verification.dest_uid == dst_uid
            )
        ).count() != 0

    @classmethod
    def _expand(cls, result):
        # Calculate and set the human readable time delta and NATO code
        result.expiry_delta = cls._approx_time_delta(
            result.expiry - datetime.utcnow()
        )
        result.nato_code = cls._nato_code(result.shared_secret)
        return result

    @staticmethod
    def _nato_code(shared_secret):
        """
        Given the shared secret, convert it into phonetic (nato) alphabetic
        codes.

        :param shared secret: the shared secret
        :rtype: the nato encoded string representation of the shared secret.
        """
        return '-'.join([NATO[letter] for letter in shared_secret])

    @staticmethod
    def _approx_time_delta(delta=None):
        """
        Given a timedelta object, given an approximation in seconds or minutes

        :param delta: a timedelta object to approximate into a string
                    representation.
        :rtype: a string containing the approximation of the timedelta.
        """
        delta = int(delta.seconds)
        unit = "second"
        if delta > 60:
            unit = "minute"
            delta /= 60
        return "{count} {unit}{plural}".format(
            count=delta,
            unit=unit,
            plural='' if delta == 1 else 's'
        )

    @staticmethod
    def _gen_shared_secret(primer):
        """
        Generate a shared secret, based on an input string. It concatenates the
        input string with a (pseudo-)random number.

        :param stuff: a string which is unique to the authentication transaction
                    to assist in the generation of random hashes.
        :rtype: the hash as a string.
        """
        salt_chars = (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789+-*/!@#$%&?"
        )
        salt = "".join(
            random.sample(salt_chars, random.randint(3, 5))
        ) + str(os.getpid())
        hashed = binascii.hexlify(hashlib.pbkdf2_hmac(
            'sha512', primer, salt, 100000
        ))
        hashlen = config.authentication.length
        if config.authentication.variable_length:
            hashlen = random.randint(hashlen - 3, hashlen)
            if hashlen < 5: hashlen = 5
        start = random.randint(0, (len(hashed) - 1) - hashlen)
        return hashed[start:start + hashlen]
