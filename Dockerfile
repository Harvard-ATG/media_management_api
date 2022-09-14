FROM python:3.8-alpine
ENV PYTHONUNBUFFERED 1
RUN apk update && apk add bash build-base curl libffi-dev postgresql-libs postgresql-dev gcc python3-dev musl-dev jpeg-dev zlib-dev
RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
ENV PATH="/etc/poetry/bin:$PATH"
RUN poetry config virtualenvs.create false
RUN poetry install --without dev
