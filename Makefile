testput:
	curl -X PUT --basic -u 'test1:test1key' --data-binary @README.txt http://127.0.0.1:6543/api/v1/test/test/README.txt

testget:
	curl -X GET --basic -u 'test1:test1key' http://127.0.0.1:6543/api/v1/test/test/README.txt -o /dev/null -s -D -


.PHONY: testput
