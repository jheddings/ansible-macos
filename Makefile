# Makefile for github tools

BASEDIR ?= $(PWD)
SRCDIR ?= $(BASEDIR)/src

APPNAME ?= $(shell grep -m1 '^name:' "$(BASEDIR)/galaxy.yml" | sed -e 's/name.*"\(.*\)"/\1/')
APPVER ?= $(shell grep -m1 '^version:' "$(BASEDIR)/galaxy.yml" | sed -e 's/version.*"\(.*\)"/\1/')

WITH_VENV := poetry run


.PHONY: all
all: venv preflight


.PHONY: venv
venv:
	poetry install --sync
	$(WITH_VENV) pre-commit install --install-hooks --overwrite


poetry.lock: venv
	poetry lock --no-update


.PHONY: static-checks
static-checks: venv
	$(WITH_VENV) pre-commit run --all-files --verbose


.PHONY: preflight
preflight: static-checks


.PHONY: build
build: venv preflight


.PHONY: github-reltag
github-reltag: preflight
	git tag "v$(APPVER)" main
	git push origin "v$(APPVER)"


.PHONY: publish
publish: build


.PHONY: release
release: publish github-reltag


.PHONY: clean
clean:
	find "$(BASEDIR)" -name "*.pyc" -print | xargs rm -f
	find "$(BASEDIR)" -name '__pycache__' -print | xargs rm -Rf


.PHONY: clobber
clobber: clean
	$(WITH_VENV) pre-commit uninstall
	poetry env remove --all
