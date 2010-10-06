VIRTUALENV = virtualenv
NOSE = bin/nosetests -s
TESTS = jpake/tests
PYTHON = bin/python
EZ = bin/easy_install

.PHONY: all build test bench_one bench bend_report

all:	build

build:
	$(VIRTUALENV) --no-site-packages --distribute .
	$(PYTHON) setup.py develop
	$(EZ) nose
	$(EZ) WebTest
	$(EZ) Funkload

test:
	$(NOSE) $(TESTS)

bench_one:
	bin/fl-run-test jpake.tests.stress StressTest.test_session -u http://localhost:5000

bench:
	cd jpake/tests; ../../bin/fl-run-bench stress StressTest.test_session -u http://localhost:5000

bench_report:
	bin/fl-build-report --html -o html jpake/tests/stress-bench.xml

