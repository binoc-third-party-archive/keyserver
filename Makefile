VIRTUALENV = virtualenv
NOSE = bin/nosetests -s
TESTS = jpake/tests
PYTHON = bin/python
EZ = bin/easy_install

.PHONY: all build test 

all:	build

build:
	$(VIRTUALENV) --no-site-packages --distribute .
	$(PYTHON) setup.py develop
	$(EZ) nose
	$(EZ) WebTest

test:
	$(NOSE) $(TESTS)
