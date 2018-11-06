FROM gcr.io/dd-decaf-cfbf6/modeling-base:master

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH /app/src

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade --process-dependency-links -r requirements.txt

COPY . /app
