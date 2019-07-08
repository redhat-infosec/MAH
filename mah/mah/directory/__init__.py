"""
Base classes for directory services.
"""

class Person(object):
    """
    Simple generic container to hold the information about a staff member.
    """
    def __init__(self, attributes):
        self.attributes = attributes
        self.uid = attributes[0]
        self.name = attributes[1]

    def ___repr__(self):
        return '<Person ' + ' - '.join(self.attributes[0:2]) + '>'

class Directory(object):
    """
    Base class that directory modules should inherit from. Directory
    modules MUST expose their child class under the name 'Directory' -
    therefore, import this like::

        from mah.directory import Directory as DirBase

        class Directory(DirBase):
            pass

    Or just refer to it by its full name like so::

        import mah.directory

        class Directory(mah.directory.Directory):
            pass
    """

    config = None
    """
    The directory section of the main app configuration. cls.config is the
    same as mah.config.config.directory. This is None until the init
    classmethod is called successfully.
    """

    @classmethod
    def init(cls, config, src):
        """
        Do class level initialisation. Should ONLY be called by the mah.config
        package on startup. config will be the same as mah.config.directory.

        :param config: directory specific configuration object. Once
                       configuration setup is complete, this will be available
                       in *mah.config.config.directory*.
        :param src: raw source config as read by ConfigParser
        """
        cls.config = config

    def search(self, query):
        """
        Search a staff directory for a staff member.

        :param str query: the query string to search with.
        :return: a list of Person (or a subclass) objects 
        :rtype: list
        """

    def user(self, uid):
        """
        Search a staff directory for a specific staff member.

        :param str uid: the user ID for a staff member to find.
        :return: a Person (or subclass) object or None 
        :rtype: mah.directory.Person
        """
