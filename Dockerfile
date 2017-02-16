FROM python:3.5-slim

RUN apt-get update -y \
    && apt-get install -y locales git-core gcc g++ netcat libxml2-dev libxslt-dev libz-dev \
    && mkdir /app

ADD . /app

ENV LANG C.UTF-8
ENV LANGUAGE C.UTF-8
ENV LC_ALL C.UTF-8

RUN cd /app; pip install -r requirements.txt --upgrade

WORKDIR /app

EXPOSE 8080

CMD [ "/usr/local/bin/pserver", "-c", "/app/config.json" ]

