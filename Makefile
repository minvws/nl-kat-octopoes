debian:
	-mkdir ./build
	docker run \
	--env PKG_NAME=kat-octopoes \
	--env BUILD_DIR=./build \
	--env REPOSITORY=minvws/nl-rt-tim-abang-octopoes \
	--env RELEASE_VERSION=${RELEASE_VERSION} \
	--env RELEASE_TAG=${RELEASE_TAG} \
	--mount type=bind,src=${CURDIR},dst=/app \
	--workdir /app \
	debian:latest \
	packaging/scripts/build-debian-package.sh

clean:
	-rm -rf build/

check: ## Check the code style using black, mypy, flake8 and pylint.
	black --diff --check .
	flake8 octopoes
	pylint --recursive=y octopoes
	mypy octopoes
	vulture octopoes

export-requirements:
	poetry export --output requirements.txt --without-hashes && \
	poetry export --output requirements-dev.txt --with dev --without-hashes
