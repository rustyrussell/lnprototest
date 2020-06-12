#! /usr/bin/make

PYTHONFILES := $(shell find * -name '*.py')

default: check-source check check-quotes

check:
	pytest $(PYTEST_ARGS)

check-source: check-flake8 check-mypy check-internal-tests

check-flake8:
	flake8 --ignore=E501,E731,W503

check-mypy:
	mypy --ignore-missing-imports $(PYTHONFILES)

check-internal-tests:
	pytest `find lnprototest -name '*.py'`

check-quotes/%: %
	tools/check_quotes.py $*

check-quotes: $(PYTHONFILES:%=check-quotes/%)

TAGS:
	etags `find . -name '*.py'`
