# syntax=docker/dockerfile:1
FROM python:3.9.6
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

ARG MYSQL_HOST
ARG MYSQL_USER
ARG MYSQL_PASSWORD
ARG MYSQL_DB
ARG SECRET_KEY

ENV MYSQL_HOST=$MYSQL_HOST
ENV MYSQL_USER=$MYSQL_USER
ENV MYSQL_PASSWORD=$MYSQL_PASSWORD
ENV MYSQL_DB=$MYSQL_DB
ENV SECRET_KEY=$SECRET_KEY

COPY . .

EXPOSE 5000
ENV PORT 5000


CMD exec gunicorn --bind :$PORT main:app --workers 1 --threads 1