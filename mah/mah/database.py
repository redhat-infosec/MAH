from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from mah.log import log

class database(object):
    engine = None
    session = None
    Base = None

    @classmethod
    def init(cls):
        """
        Initialised the database connection for SQL Alchemy.
        """
        from mah.config import config # Delayed to ensure it's loaded
        if not config.ok: return
        cls.engine = create_engine(
            config.database.connect,
            convert_unicode=True,
            pool_recycle=3600
        )
        if config.database.logsql:
            cls.engine.logger = log
        cls.session = scoped_session(sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine
        ))
        cls.Base = declarative_base()
        cls.Base.query = cls.session.query_property()

        import mah.verification # Get the table definition loaded

        try:
            cls.Base.metadata.create_all(bind=cls.engine) ####!
        except Exception as e:
            log.error("Failed to connect to database: {err}.".format(
                err=e
            ))
            raise

    @classmethod
    def done(cls, ok=False):
        if ok:
            cls.session.commit() # pylint: disable=E1101
        else:
            cls.session.rollback() # pylint: disable=E1101
        cls.session.remove()
