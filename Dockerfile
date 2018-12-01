FROM python:3.6

RUN mkdir -p /storage/blobs
RUN mkdir /code
WORKDIR /code

RUN apt-get -y update && apt-get -y install libpq-dev

COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY requirements.txt /code

RUN pip install -r requirements.txt
COPY . /code
RUN python setup.py develop
