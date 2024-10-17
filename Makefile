.PHONY: pyright

pyright:
	python scripts/run-pyright.py --all

install_pyright:
	pip install -e 'python_modules/dagster[pyright]' -e 'python_modules/dagster-pipes'

rebuild_pyright:
	python scripts/run-pyright.py --all --rebuild

rebuild_pyright_pins:
	python scripts/run-pyright.py --update-pins --skip-typecheck

quick_pyright:
	python scripts/run-pyright.py --diff

unannotated_pyright:
	python scripts/run-pyright.py --unannotated

ruff:
	-ruff check --fix .
	ruff format .

check_ruff:
	ruff check .
	ruff format --check .

install_dev_python_modules:
	python scripts/install_dev_python_modules.py -qqq

install_dev_python_modules_verbose:
	python scripts/install_dev_python_modules.py

install_dev_python_modules_verbose_m1:
	python scripts/install_dev_python_modules.py -qqq --include-prebuilt-grpcio-wheel

sanity_check:
	@echo Checking for prod installs - if any are listed below reinstall with 'pip -e'
	@! (pip list --exclude-editable | grep -e dagster | grep -v dagster-hex | grep -v dagster-hightouch)

dev_install_m1_grpcio_wheel: install_dev_python_modules_verbose_m1

dev_install: install_dev_python_modules_verbose

dev_install_quiet: install_dev_python_modules

graphql_tests:
	pytest python_modules/dagster-graphql/dagster_graphql_tests/graphql/ -s -vv

check_manifest:
	check-manifest python_modules/dagster
	check-manifest python_modules/dagster-webserver
	check-manifest python_modules/dagster-graphql
	ls python_modules/libraries | xargs -n 1 -Ipkg check-manifest python_modules/libraries/pkg
