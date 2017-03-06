FROM python:3.5-slim

RUN mkdir -p /data/blobstorage

RUN apt-get update -y \
    && apt-get install -y locales git-core gcc g++ netcat libxml2-dev libxslt-dev libz-dev \
    && pip install ZEO

COPY zeo.cfg /etc/zeo.cfg

EXPOSE 8100
CMD [ "runzeo", "-C", "/etc/zeo.cfg" ]
