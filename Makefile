# Makefile for ansible-macos

-include local.env

BASEDIR ?= $(PWD)
SRCDIR ?= $(BASEDIR)/src

APPNS ?= $(shell grep -m1 '^namespace:' "$(BASEDIR)/galaxy.yml" | sed -e 's/name.*"\(.*\)"/\1/')
APPNAME ?= $(shell grep -m1 '^name:' "$(BASEDIR)/galaxy.yml" | sed -e 's/name.*"\(.*\)"/\1/')
APPVER ?= $(shell grep -m1 '^version:' "$(BASEDIR)/galaxy.yml" | sed -e 's/version.*"\(.*\)"/\1/')

BUILD_DIR ?= $(BASEDIR)/build
BUILD_TGZ ?= $(APPNS)-$(APPNAME)-$(APPVER).tar.gz
BUILD_FILE ?= $(BUILD_DIR)/$(BUILD_TGZ)

WITH_VENV := poetry run

export


.PHONY: all
all: venv preflight


.PHONY: venv
venv:
	poetry sync
	$(WITH_VENV) pre-commit install --install-hooks --overwrite


poetry.lock: venv
	poetry lock


.PHONY: static-checks
static-checks: venv
	$(WITH_VENV) pre-commit run --all-files --verbose


.PHONY: preflight
preflight: static-checks


.PHONY: build
build: venv preflight
	$(WITH_VENV) ansible-galaxy collection build "$(BASEDIR)" \
		--output-path "$(BUILD_DIR)"


.PHONY: github-reltag
github-reltag: preflight
	git tag "v$(APPVER)" main
	git push origin "v$(APPVER)"


.PHONY: publish
publish: venv preflight build
	$(WITH_VENV) ansible-galaxy collection publish \
		--token "${ANSIBLE_GALAXY_TOKEN}" "$(BUILD_FILE)"


.PHONY: release
release: preflight publish github-reltag
	echo "Released $(APPNAME)-$(APPVER)"


.PHONY: clean
clean:
	rm -Rf "$(BUILD_DIR)"
	find "$(BASEDIR)" -name "*.pyc" -print | xargs rm -f
	find "$(BASEDIR)" -name '__pycache__' -print | xargs rm -Rf


.PHONY: clobber
clobber: clean
	$(WITH_VENV) pre-commit uninstall
	poetry env remove --all
