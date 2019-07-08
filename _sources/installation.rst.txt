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
