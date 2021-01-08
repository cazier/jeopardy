FROM alpine:latest

RUN apk add bash python3 python3-dev gcc musl-dev python3-pip

RUN addgroup -S www-data && adduser -S jeopardy -G www-data
COPY . /home/jeopardy/app

WORKDIR /home/jeopardy/app

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt