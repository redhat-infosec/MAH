"""
Base classes for authentication services.
"""

class Authentication(object):
    """
    Base class that authentication modules should inherit from. Authentication
    modules MUST expose their child class under the name 'Authentication' -
    therefore, import this like::

        from mah.authentication import Authentication as AuthBase

        class Authentication(AuthBase):
            pass

    Or just refer to it by its full name like so::

        import mah.authentication

        class Authentication(mah.authentication.Authentication):
            pass
    """
    inputs = {
        'username': {
            'name': 'username',
            'label': 'Username',
            'secret': False,
            'required': True,
            'description': None,
            'order': 1
        },
        'password': {
            'name': 'password',
            'label': 'Password',
            'secret': True,
            'required': True,
            'description': None,
            'order': 2
        }
    }
    """
    A dictionary of fields accepted by the authenticator. Each key should be a
    field name (ie, will be used in an <input> tag as the name attribute) with
    a value of a dict describing the key. That dict should have the following
    keys.

    name
        The name of the field (ie, identical to the key of this input).
    label
        Display name for the field. This should be changable in config by using
        a \*_label configuration variable.
    secret
        If True, the field will be considered password-like and a type of
        'password' will be used for the <input> tag instead of 'text'.
    required
        Boolean. Can be used to modify the interface, however the authenticator
        MUST check validity itself.
    description
        None, or a text string that will be displayed near the input to describe
        what is expected. This should be changable in config by using a
        \*_description configuration variable.
    order
        A number defining in which order (ascending) the fields should be shown.
        If two fields have the same order, they will be sorted correctly in
        respect to all other fields, but will not be reliably ordered amongst
        themselves.
    """
    config = None
    """
    The login section of the main app configuration. cls.config is the
    same as mah.config.config.login. This is None until the init classmethod is
    called successfully.
    """
    _template_inputs = None

    @classmethod
    def init(cls, config, src):
        """
        Initialise the authenticator. By default we make sure the username and
        password inputs are updated by the config, and we store the config for
        future use
    
        :param config: login specific configuration object. Once configuration
                       setup is complete, this will be available in
                       *mah.config.config.login*.
        :param src:    raw source config as read by ConfigParser
        """
        cls.inputs['username']['label'] = src.str(
            'username_label', cls.inputs['username']['label']
        )
        cls.inputs['username']['description'] = src.str(
            'username_description', cls.inputs['username']['description']
        )
        cls.inputs['password']['label'] = src.str(
            'password_label', cls.inputs['password']['label']
        )
        cls.inputs['password']['description'] = src.str(
            'password_description', cls.inputs['password']['description']
        )
        cls.config = config

    @classmethod
    def authenticate(cls, form):
        """
        The main authentication method. Takes a form (a dict of form field names
        to string values), and uses the data therein to authenticate the user.
        Should return a tuple of the username and whether authentication was
        successful.

        :param form: A form object (dict-like) with fields entered by the user
        :return: A 2-tuple of username (str) and success (bool)
        """
        raise NotImplementedError()

    @classmethod
    def template_inputs(cls):
        """
        Reorganises the inputs to a form more consumable by templates
        """
        if cls._template_inputs is None:
            cls._template_inputs = sorted(
                cls.inputs.values(), key=lambda x: x['order']
            )
        return cls._template_inputs

    @staticmethod
    def for_production():
        """
        If this is a 'dummy' authentication method (like the built in 'none'
        authentication module), this should return False - a warning will be
        displayed on the login page.
        """
        return True
