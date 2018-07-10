
[![Build Status](https://travis-ci.org/Harvard-ATG/media_management_api.svg)](https://travis-ci.org/Harvard-ATG/media_management_api)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/Harvard-ATG/media_management_api/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/Harvard-ATG/media_management_api/?branch=master)

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
$ open http://localhost:8000
```

**Other tasks:**

- Access postgres database: `docker-compose exec db psql -U media_management_api`
- Run unit tests: `docker-compose exec web python manage.py test`

