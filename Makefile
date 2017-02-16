example_docker_commands:
	docker build -t pserver-reliquary .
	docker run -p 8080:8080 -it --rm --name pserver-reliquary-running pserver-reliquary


testput:
	curl -X PUT --basic -u 'test1:test1key' --data-binary @README.txt http://127.0.0.1:6543/api/v1/test/test/README.txt

testget:
	curl -X GET --basic -u 'test1:test1key' http://127.0.0.1:6543/api/v1/test/test/README.txt -o /dev/null -s -D -


.PHONY: testput
