#! /usr/bin/make

default: check-source check check-quotes

check:
	pytest $(PYTEST_ARGS)

check-source:
	flake8 --ignore=E501,E731,W503

PYTHONFILES := $(shell find * -name '*.py')

check-quotes/%: %
	tools/check_quotes.py $*

check-quotes: $(PYTHONFILES:%=check-quotes/%)

TAGS:
	etags `find . -name '*.py'`
