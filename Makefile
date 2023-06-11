VERSION := $(shell cat VERSION)

distribute:
	conda run -n papnt python setup.py sdist
	shasum -a 256 dist/papnt-$(VERSION).tar.gz | cut -d ' ' -f 1
