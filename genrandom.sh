#! /bin/bash
for n in $(seq 1 1000); do
    dd if=/dev/urandom of=/storage/blobs/test/test/file-$( printf %03d "$n" ).bin bs=1 count=$(( RANDOM + 1024 ))
done
