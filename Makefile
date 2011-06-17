APPNAME = server-key-exchange
DEPS = server-core
VIRTUALENV = virtualenv
NOSE = bin/nosetests -s --with-xunit
TESTS = keyexchange/tests
PYTHON = bin/python
COVEROPTS = --cover-html --cover-html-dir=html --with-coverage --cover-package=keyexchange
COVERAGE = bin/coverage
PYLINT = bin/pylint
PKGS = keyexchange
BUILD = bin/buildapp
PYPI = http://pypi.python.org/simple
PYPI2RPM = bin/pypi2rpm.py --index=$(PYPI)
PYPIOPTIONS = -i $(PYPI)
EZ = bin/easy_install
EZOPTIONS = -U -i $(PYPI)
BENCH_CYCLE = 10
BENCH_DURATION = 10
BENCH_SCP =

ifdef TEST_REMOTE
	BENCHOPTIONS = --url $(TEST_REMOTE) --cycle $(BENCH_CYCLE) --duration $(BENCH_DURATION)
else
	BENCHOPTIONS = --cycle $(BENCH_CYCLE) --duration $(BENCH_DURATION)
endif


ifdef PYPIEXTRAS
	PYPIOPTIONS += -e $(PYPIEXTRAS)
	EZOPTIONS += -f $(PYPIEXTRAS)
endif

ifdef PYPISTRICT
	PYPIOPTIONS += -s
	ifdef PYPIEXTRAS
		HOST = `python -c "import urlparse; print urlparse.urlparse('$(PYPI)')[1] + ',' + urlparse.urlparse('$(PYPIEXTRAS)')[1]"`

	else
		HOST = `python -c "import urlparse; print urlparse.urlparse('$(PYPI)')[1]"`
	endif
	EZOPTIONS += --allow-hosts=$(HOST)
endif

EZ += $(EZOPTIONS)

.PHONY: all build test bench_one bench bend_report build_rpms hudson lint functest

all:	build

build:

	$(VIRTUALENV) --no-site-packages --distribute .
	$(EZ) MoPyTools
	$(BUILD) $(PYPIOPTIONS) $(APPNAME) $(DEPS)
	$(EZ) nose
	$(EZ) WebTest
	$(EZ) funkload
	$(EZ) pylint
	$(EZ) coverage
	$(EZ) pypi2rpm
	$(EZ) wsgi_intercept
	$(EZ) WSGIProxy

test:
	$(NOSE) $(TESTS)

bench_one:
	cd keyexchange/tests; ../../bin/fl-run-test keyexchange.tests.stress StressTest.test_channel_put_get

bench:
	- cd keyexchange/tests; ../../bin/fl-run-bench $(BENCHOPTIONS) stress StressTest.test_channel_put_get
	$(BENCH_SCP)

bench_report:
	bin/fl-build-report --html -o html keyexchange/tests/keyexchange.xml

hudson:
	rm -f coverage.xml
	- $(COVERAGE) run --source=keyexchange $(NOSE) $(TESTS); $(COVERAGE) xml

lint:
	rm -f pylint.txt
	- $(PYLINT) -f parseable --rcfile=pylintrc $(PKGS) > pylint.txt

build_rpms:
	rm -rf $(CURDIR)/rpms
	mkdir $(CURDIR)/rpms
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms cef
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms WebOb --version=1.0
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms Paste --version=1.7.5.1
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms PasteDeploy --version=1.3.4
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms PasteScript --version=1.7.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms Mako --version=0.3.4
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms MarkupSafe --version=0.11
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms Beaker --version=1.5.4
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms python-memcached --version=1.45
	rm -rf build; $(PYTHON) setup.py --command-packages=pypi2rpm.command bdist_rpm2 --spec-file=KeyExchange.spec --dist-dir=$(CURDIR)/rpms --binary-only
	cd deps/server-core; rm -rf build; ../../$(PYTHON) setup.py --command-packages=pypi2rpm.command bdist_rpm2 --spec-file=Services.spec --dist-dir=$(CURDIR)/rpms --binary-only
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms simplejson --version=2.1.1
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms Routes --version=1.12.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms SQLAlchemy --version=0.6.6
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms MySQL-python --version=1.2.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms WSGIProxy --version=0.2.2

mach: build build_rpms
	mach clean
	mach yum install python26 python26-setuptools
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla-services/gunicorn-0.11.2-1moz.x86_64.rpm
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla/nginx-0.7.65-4.x86_64.rpm
	mach yum install rpms/*
	mach chroot python2.6 -m keyexchange.run

mock: build build_rpms
	mock clean
	mock --install python26 python26-setuptools
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla-services/gunicorn-0.11.2-1moz.x86_64.rpm
	cd rpms; wget http://mrepo.mozilla.org/mrepo/5-x86_64/RPMS.mozilla/nginx-0.7.65-4.x86_64.rpm
	mock --install rpms/*
	mock --chroot "python2.6 -m keyexchange.run"
