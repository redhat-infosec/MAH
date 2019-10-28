FROM python:2-alpine

RUN pip install six ldap3 pyrad flask flask-sqlalchemy flask-seasurf && \
    pip install m2r sphinx sphinx_rtd_theme

RUN apk --update --no-cache add \
    bash \
    coreutils \
    figlet \
    make \
    && apk upgrade

WORKDIR /app

ENTRYPOINT ["make"]