--
-- Schema creation for the MAH application.
--
-- See also the mah.conf (application configuration) file for database
-- connection configuration. The default location for mah.conf is: 
-- /var/www/wsgi/mah/mah.conf
--

CREATE USER 'auth'@'localhost' IDENTIFIED BY 'password1';

CREATE DATABASE authdb;

GRANT ALL ON authdb.* TO 'auth'@'localhost';

CREATE TABLE authdb.authentications (
  auth_id int(11) NOT NULL AUTO_INCREMENT,
  source_uid varchar(32) NOT NULL,
  source_name varchar(200) NOT NULL,
  dest_uid varchar(32) NOT NULL,
  dest_name varchar(200) NOT NULL,
  shared_secret varchar(128) NOT NULL,
  expiry datetime NOT NULL,
  reciprocated tinyint(1) NOT NULL,
  PRIMARY KEY (auth_id)
)
