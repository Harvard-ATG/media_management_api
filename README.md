
[![Build Status](https://travis-ci.org/Harvard-ATG/media_management_api.svg)](https://travis-ci.org/Harvard-ATG/media_management_api)
![Coverage Status](./coverage.svg)

### Quickstart

**Prerequisites:**

Ensure that [docker](https://www.docker.com/) is installed.

**Configure django:**

```
$ cp media_management_api/settings/secure.py.example media_management_api/settings/secure.py
```

**Start docker services:**

```
$ docker-compose up
$ docker-compose exec web python manage.py migrate
$ docker-compose exec web python manage.py createsuperuser
$ open http://localhost:9000
```

**If you have not created the docker image yet before the previous step**
```
$ docker build -t harvard-atg/media_management_api .
$ docker tag harvard-atg/media_management_api:latest harvard-atg/media_management_api:dev
```

### Setting up dev environment

**Dependencies**

The requirements are stored in `pyproject.toml`, and `poetry.lock` contains the actual dependencies as installed in the virtual environment that can be used for development. Poetry installation instructions are available in [Poetry documentation](https://python-poetry.org/docs/).

With poetry installed, you can specify a python executable with `poetry env use /path/to/python`, so it plays nice with [pyenv](https://github.com/pyenv/pyenv). Then a `poetry install` will install dependencies and `poetry shell` will get you into the environment. Add dependencies with `poetry add packagename`, or `poetry add --dev packagename` for dev dependencies. Check out [Poetry documentation](https://python-poetry.org/docs/) for a full overview.

**Pre-commit hooks**

After setting up and activating your environment, run
```
pre-commit install
```
to set up pre-commit hooks, then run
```
pre-commit run --all-files
```
to make sure that it works. Once configured, the pre-commit hooks will enforce code style standards on commit locally, so you can reformat your code before pushing upstream.

### Other tasks

- Access postgres database: `docker-compose exec db psql -U media_management_api`
- Run unit tests: `docker-compose exec web python manage.py test`


**Update the Coverage Badge**

```
$ coverage run --source='.' manage.py test
$ coverage-badge -f -o coverage.svg
```
- Then commit and push the changes!
