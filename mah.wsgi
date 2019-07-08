import sys
import os

os.environ['MAHCONFIG'] = '/var/www/wsgi/mah/mah.conf'
sys.path.insert(0, "/var/www/wsgi/mah")

from mah import app as application
