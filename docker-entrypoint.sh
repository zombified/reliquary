#!/bin/bash

mkdir -p /storage/blobs
init_reliquary /code/etc/docker.ini

exec "$@"
