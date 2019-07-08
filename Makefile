templates = mah/templates/*
static_files = mah/static/*
sources = mah/*.py mah/mah.conf
config = mah.conf mah.wsgi Makefile
docsource = mah/doc/Makefile mah/doc/source
tarball = mah-$(shell cat VERSION).tar.gz
rpmbuild = ~/rpmbuild

export MAHCONFIG = $(shell pwd)/mah/mah.conf

build: tarball mah.spec
	cp $(tarball) $(rpmbuild)/SOURCES
	rpmbuild -ba mah.spec

docs: $(docsource)
	make -C mah/doc text
	cp mah/doc/build/text/README.txt README

htmldocs: $(docsource)
	make -C mah/doc html

tarball: $(sources) $(templates) $(static_files) $(config) AUTHORS VERSION mah.sql docs
	tar czf $(tarball) $(sources) $(templates) $(static_files) $(config) README AUTHORS VERSION mah.sql

install:
	mkdir -p $(DESTDIR)/var/www/wsgi/
	cp mah.wsgi $(DESTDIR)/var/www/wsgi/
	cp -r mah $(DESTDIR)/var/www/wsgi/
	mkdir -p $(DESTDIR)/etc/httpd/conf.d/
	cp mah.conf $(DESTDIR)/etc/httpd/conf.d/
	# echo 'WSGISocketPrefix /var/run/wsgi' >> $(DESTDIR)/etc/httpd/conf.d/wsgi.conf

clean:
	rm README
	rm $(tarball)
