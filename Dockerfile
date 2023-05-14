FROM python:3.10
LABEL autor="PARSER"
LABEL description="HTML_PARSER"

WORKDIR /usr/src/html_parser/
COPY . /usr/src/html_parser/

RUN apt-get update

RUN echo "Y" | apt-get install alien
RUN echo "Y" | apt-get install gunicorn
RUN echo "Y" | apt-get install memcached
RUN echo "Y" | apt-get install unixodbc
RUN echo "Y" | apt-get install unixodbc-dev
RUN echo "Y" | apt-get install cifs-utils

RUN apt-get install libaio1

ENV pip=pip3
ENV python=python3
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt


RUN apt-get update --allow-releaseinfo-change
RUN Xvfb &

EXPOSE 4323

EXPOSE 4324
EXPOSE 4325
EXPOSE 4326
EXPOSE 4327
