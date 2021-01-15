FROM python:3.9.1-alpine AS app

### BUILD STAGE
FROM app as builder

RUN apk add --no-cache python3-dev g++ musl-dev py3-pip

COPY requirements.txt /requirements.txt

RUN python -m venv /venv

ENV PATH="/venv/bin:$PATH"

RUN python -m pip install --upgrade pip wheel
RUN python -m pip install -r /requirements.txt

### APP STAGE
FROM app

RUN addgroup -S www-data && adduser -S jeopardy -G www-data
COPY . /home/jeopardy/app
COPY --from=builder /venv/ /home/jeopardy/app/venv

WORKDIR /home/jeopardy/app

EXPOSE 5000
ENV PATH="/home/jeopardy/app/venv/bin:$PATH"

CMD ["python", "/home/jeopardy/app/jeopardy/web.py"]