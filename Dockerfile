FROM python:3.9.1-alpine

RUN apk add bash python3 python3-dev gcc musl-dev py3-pip

RUN addgroup -S www-data && adduser -S jeopardy -G www-data
COPY . /home/jeopardy/app

WORKDIR /home/jeopardy/app

RUN python3 -m pip install --upgrade pip setuptools
### CURRENTLY BREAKING ON PKG-RESOURCES==0.0.0
RUN python3 -m pip install -r requirements.txt

RUN apk add --no-cache tini

ENTRYPOINT ["/sbin/tini", "--"]

EXPOSE 5000

CMD ["/usr/bin/python3", "/home/jeopardy/app/jeopardy/web.py"]