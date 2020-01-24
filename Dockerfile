FROM python:3.8-alpine
ENV PYTHONUNBUFFERED 1
RUN apk update && apk add bash build-base postgresql-libs postgresql-dev gcc python3-dev musl-dev jpeg-dev zlib-dev
RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN pip install -r media_management_api/requirements/base.txt
