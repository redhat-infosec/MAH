MAH README version 1.0.1

Mutual Authentication for Humans (MAH)
======================================

This system allows a user to easily verify another user as an employee of
the same organisation. It does this by allowing users to create a shared
secret, a short text string. Access to this system should be allowed via a
the strongest possible authentication mechanism available to an
organisation, for example, RSA 2 factor tokens.


Installation
============
MAH can be installed via packages or manually from source.

Installation Requirements
-------------------------
The Mutual Authentication for Humans (MAH) requires numerous supporting
software packages and services.

* The Python interpreter 'python' - installed by default. (MAH has been tested with both Python versions 2.6 and 2.7)

* A web server (e.g. Apache using WSGI)

* A database (e.g. MySQL)

* The `Flask <http://flask.pocoo.org/>`_ micro-framework, which in turn relies on `Werkzeug <http://werkzeug.pocoo.org/>`_ and `Jinja 2 <http://jinja.pocoo.org/>`_ (*Important:* Jinja2 version must be 2.6 or higher).

* The `SQL Alchemy <http://www.sqlalchemy.org/>`_ SQL tool kit and Object Relational Mapper.

* SeaSurf, a CSRF protection wrapper for Flask.

* The Python Radius API, pyrad and Radius server which is configured to allow the system running MAH to be a NAS (Network Access Server).

* The Python LDAP API, ldap and (read-only) access to an LDAP directory.


Installation instructions
-------------------------

Manual Installation
```````````````````

Pre-requisite package installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Apache and MySQL (if needed) and allow connectivity to port 80/443.
::

    # wget http://repo.mysql.com/mysql-community-release-el7-5.noarch.rpm -P /rootwget http://repo.mysql.com/mysql-community-release-el7-5.noarch.rpm
    # sudo rpm -ivh mysql-community-release-el7-5.noarch.rpmsudo rpm -ivh mysql-community-release-el7-5.noarch.rpm
    # yum install httpd mod_wsgi mysql-server MySQL-python

2. Install Flask, SQL Alchemy, pyrad, and ldap (and dependancies). Additional python packages will be installed by pip
::

    # yum install python-pip python-sqlalchemy

3. Install packages (not available as an rpm) via pip
::

    # pip install pyrad flask flask-sqlalchemy flask-seasurf six pip3

Download and setup MAH
``````````````````````

4. Download and extract the source tree from the git repository.
::

  # wget https://<source>.tar.gz
  # tar xzf <name>.tar.gz
  # cd mah-*

5. Copy the mah code into the webserver directory.
::

    # mkdir /var/www/wsgi/
    # cp -r {mah,mah.wsgi} /var/www/wsgi


Configuring the web server
``````````````````````````
6. Install apache config
::

    # cp mah.conf /etc/httpd/conf.d/

7. Add the following line to /etc/httpd/conf.d/wsgi.conf to prevent SElinux
alerts, if required.
::

    WSGISocketPrefix /var/run/wsgi

Setting up MySQL
````````````````
8. Running the following MySQL commands as root (or similar DBA account)
will set up the required tables.
::

    mysql> create database authdb;
    mysql> create user 'auth'@'localhost' identified by 'password';
    mysql> grant all on authdb.* to 'auth'@'localhost';
    mysql> flush privileges;

   #useful commands: systemctl start mysqld.service; mysql_secure_installation; select * from authentication;

and this dictates the following configuration:
::

    [database]
    connect = mysql://auth:password1@localhost/authdb


SELinux configuration
`````````````````````
The folloing SE Linux policy modules are required for the application to
initiate LDAP and SMTP connections.
::

    module httpd_wsgi_socket 1.0;

    require {
        type httpd_log_t;
        type httpd_t;
        class sock_file create;
    }

    #============= httpd_t ==============
    allow httpd_t httpd_log_t:sock_file create;

    module httpd_ldap_connect 1.0;

    require {
        type ldap_port_t;
        type httpd_t;
        class tcp_socket name_connect;

    }

    #============= httpd_t ==============
    allow httpd_t ldap_port_t:tcp_socket name_connect;

    module httpd_smtp_connect 1.0;

    require {
        type httpd_t;
        type smtp_port_t;
        class tcp_socket name_connect;
    }
    allow httpd_t smtp_port_t:tcp_socket name_connect;


Further configuration
`````````````````````
Additional configuration of the applciation is recommended, particular the
use of HTTPS, before Radius authentication is enabled.

For a complete list of configuration options, please see the
:doc:`configuration` page.

Troubleshooting
---------------
Apache errors will be report, by default, in /var/log/http/error_log.
Application errors will be reported in the MAH log file or via syslog (see
:doc:`configuration` page for details on the logging options).

Running the application manually may provide additional debugging
information:
::

    /var/www/wsgi/mah/mah.py

This, by default, will start the application using the builtin Werkzeug
http server, on localhost and port 5000 by default (editable in mah.conf)

Configuration
=============
The configuration for MAH is handled via the standard Python `ConfigParser <http://docs.python.org/library/configparser.html>`_ framework, which uses the Microsoft INI file structure.


location
--------
The location of the configuration file can be specified via the environment
variable MAHCONFIG.

Example (for Bourne compatible shells):
::

    export MAHCONFIG=/path/to/config/mah.conf

sample configuration
--------------------
The following shows an example configuration file:

Example mah.conf
::

    [database]
    connect = mysql://<username>:<password>@<host>/<database>
    logsql = False

    [ldap]
    size_limit = 50 ;max count of findings
    paged_size = 10
    time_limit = 50
    server = ldap://<hostname>:<port> ;for ssl use ldaps:
    user = admin
    password = 12345
    scope = ou=users, dc=corp, dc=com
    attributes = uid,cn,title,mail,telephoneNumber,location
    filter = uid,cn,telephoneNumber
    attributes = uid,cn,title,mail,telephoneNumber,location
    id_attribute = uid
    web_attributes = Username,Full Name,Title,Email,Phone,Location


    [login]
    check_password = True
    use_radius = True
    radius_dictionary = /usr/share/doc/python-pyrad-1.1/example/dictionary
    radius_server = <hostname>
    radius_secret = <password>
    radius_nas_identifer = 1
    radius_nas_ip_address = <ip_address>

    [authentication]
    timeout = 600
    length = 9
    variable_length = True

    [report]
    email_from = mah@corp.com
    email_to = user@corp.com
    email_subject = MAH suspicious activity report
    smtp_server = smtp.corp.com

    [application]
    host = 0.0.0.0
    port = 5000
    SESSION_KEY = SomeSort0fRandomStringShouldGoHere?
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = https
    SESSION_TIMEOUT = 600
    REFRESH = 30

    [logging]
    file_name = ./mah.log
    file_level = DEBUG
    syslog_level = INFO
    syslog_facility =  local1
    syslog_host = localhost
    syslog_port = 514

configuration elements
----------------------
This section provides a description of all the configuration elements,
including their use and function. The configuration elements are described
in the form section.variable.

database.connection
```````````````````
The database connection string.
::

    <engine>://<db-user>:<db-password>@<db-host>/<database>

This is the argument provided to the create_engine() function of SQL Alchemy. For more
information, see `the SQL Alchemy documentation <http://docs.sqlalchemy.org/en/rel_0_7/core/engines.html>`_ for more information.

database.logsql
```````````````
Enable logging of SQL statements.
::

    logsql = False

Use this configuration option to enable or disable SQL logging for
debugging purposes.

ldap.size_limit
```````````````
Global limit - sets how many entries the server will examine.
Count of staff on a page.
::

    size_limit = 250

ldap.paged_size
```````````````
Global limit - sets maximum page size.
Microsoft Active Directory function.
::

    paged_size = 5

ldap.time_limit
```````````````
Global limit - sets maximum time limit.
::

        time_limit = 30

ldap.server
```````````
The LDAP server URL to connect to. For SSL use ldaps:
::

    ldap://<address>:<port>

ldap.user and ldap.password
```````````````````````````
Login credentials into LDAP server.
::

    user = admin
    password = 12345

ldap.scope
``````````
The LDAP scope in which to perform directory searches.
::

    scope = ou=users, dc=corp, dc=com

ldap.filter
```````````
The LDAP filter specify final results based on terms.
::

    filter =  uid,cn,telephoneNumber

ldap.attributes
```````````````
The LDAP attributes specify directory searches.
::

    attributes = cn,uid,title,mail,telephoneNumber,location

ldap.id_attribute
`````````````````
The LDAP id_attribute specify search_by_uid attribute for searches.
::

    id_attribute = uid

ldap.web_attributes
```````````````````
The LDAP web_attributes specify description of every column in table on web
page. Used in the same order as 'ldap.attributes'
::

    web_attributes = Username,Full Name,Title,Email,Phone,Location


login.check_password
````````````````````
A Boolean (True/False) option to determine if passwords should be (required
and) checked in order to log in to MAH.

**This should always be set to True for production systems.**.

If set to False, the following log entry will be generated on start up:
::

    WARNING: Password checks are configured NOT to be enforced.

login.use_radius
````````````````
Should the login system authenticate users using Radius. If set to true,
the further login.radius_* settings are required.

login.radius_dictionary
```````````````````````
The radius dictionary to use, the default which is installed with pyrad is
generally sufficient.
::

    radius_dictionary = /usr/share/doc/python-pyrad-1.1/example/dictionary

login.radius_server
```````````````````
The radius server host name which should be used to authenticate users.
::

    radius_server = <RADIUS_hostname>

login.radius_secret
```````````````````
The radius shared secret for this application/host to use when
communicating with the Radius server.

login.radius_nas_identifer
``````````````````````````
The host name of the Network Access Server (the server running the MAH
application).
::

    radius_nas_identifer = <NAS_identifer>

login.radius_nas_ip_address
```````````````````````````
The IP of the Network Access Server (the server running the MAH
application).
::

    radius_nas_ip_address = <NAS_address>

authentication.timeout
``````````````````````
When one user authenticates another, the length of time (in seconds) that
the shared secret be visible to both users. It is prudent to have
relatively short (minutes, as opposed to hours) authentication timeouts.
::

    timeout = 600

authentication.length
`````````````````````
The length of the authentication shared secret.
::

    length = 9

authentication.length
`````````````````````
Allow variable length of the authentication shared secret in interval
<length/length-3>.
::

    variable_length = true

report.email_from
`````````````````
The from email address to use when send suspicious reports.
::

    email_from = <mutual_email>

report.email_to
```````````````
The to address to send suspicious reports to for further investigation.
::

    email_to = <admin_email>

report.email_subject
````````````````````
The subject to use for suspicious reports. Currently, there is no support
for templates/variables, so the subject must be a static string.
::

    email_subject = MAH suspicious activity report

report.smtp_server
``````````````````
The SMTP email server to use for sending suspicious activity reports.
::

    smtp_server = <SMTP_address>

application.host and application.port
`````````````````````````````````````
The host address and port of MAH application.
::

    host = 0.0.0.0
    port = 5000

application.SESSION_KEY
```````````````````````
The key used by Flask to encrypt session information stored in the cookie.

See also: `Flask Configuration Handling <http://flask.pocoo.org/docs/config/>`_

application.SESSION_COOKIE_SECURE
`````````````````````````````````
Controls if the cookie should have the secure flag set.
::

    SESSION_COOKIE_SECURE = True

See also: `Flask Configuration Handling <http://flask.pocoo.org/docs/config/>`_

application.SESSION_COOKIE_HTTPONLY
```````````````````````````````````
Controls if the cookie should have the httponly flag set.
::

    SESSION_COOKIE_HTTPONLY = True

See also: `Flask Configuration Handling <http://flask.pocoo.org/docs/config/>`_

application.PREFERRED_URL_SCHEME
````````````````````````````````
The preferred URL generation scheme, default is http.
::

    PREFERRED_URL_SCHEME = https

See also: `Flask Configuration Handling <http://flask.pocoo.org/docs/config/>`_

application.SESSION_TIMEOUT
```````````````````````````
The period of inactivity (in seconds) after which a user's session will be
invalidated and they will be required to log in again to continue.
::

    SESSION_TIMEOUT = 600

**Note:** if a application.REFRESH is set at a rate lower than
SESSION_TIMEOUT, then this may counteract the intended function of this
variable. In such a situation the (index) page would continually refresh
preventing the TIMEOUT threshold from ever being met.

application.REFRESH
```````````````````
How often (in seconds) should the index page automatically refresh. This is
::

    REFRESH = 30

logging.file_name
`````````````````
The file name of log file (if one is configured).
::

    file_name = ./mah.log

logging.file_level
``````````````````
The level of verbosity of messages logged to file. Valid levels are:
 * NONE - disable file logging
 * DEBUG - emit debugging level information and higher
 * INFO - emit general application information and higher
 * WARN - emit application warnings and higher
 * ERROR - emit error messages and higher
 * CRITICAL - emit critical messages only

::

    file_level = DEBUG

logging.syslog_level
````````````````````
The level of verbosity of messages logged via syslog. Valid levels are:
 * NONE - disable file logging
 * DEBUG - emit debugging level information and higher
 * INFO - emit general application information and higher
 * WARN - emit application warnings and higher
 * ERROR - emit error messages and higher
 * CRITICAL - emit critical messages only

::

    syslog_level = INFO

logging.syslog_facility
```````````````````````
The syslog facility to use. For more complete information on syslog
facilities, please see the `<logging.handlers.SysLogHandler documentation
<http://docs.python.org/dev/library/logging.handlers.html#logging.handlers.SysLogHandler>`_.
::

    syslog_facility =  local1

logging.syslog_host
```````````````````
The host to send syslog messages to.
::

    syslog_host = localhost

logging.syslog_port
```````````````````
The UDP port to send syslog messages to.
::

    syslog_port = 514


