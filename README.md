
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

**Other tasks:**

- Access postgres database: `docker-compose exec db psql -U media_management_api`
- Run unit tests: `docker-compose exec web python manage.py test`


**Update the Coverage Badge**

```
$ coverage run --source='.' manage.py test
$ coverage-badge -f -o coverage.svg
```
- Then commit and push the changes!
