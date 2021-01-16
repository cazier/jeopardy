FROM python:3.9.1-alpine AS app

### BUILD STAGE
FROM app as builder

COPY requirements.txt /requirements.txt
RUN sed -i 's/lxml.*//' /requirements.txt


RUN python -m venv /venv

ENV PATH="/venv/bin:$PATH"

RUN python -m pip install --upgrade pip wheel
RUN python -m pip install -r /requirements.txt


### APP STAGE
FROM app

RUN addgroup -S www-data && adduser -S jeopardy_data -G www-data
COPY . /home/jeopardy_data/app
COPY --from=builder /venv/ /home/jeopardy_data/app/venv

WORKDIR /home/jeopardy_data/app

RUN sed -i 's/lxml/html.parser/g' jeopardy_data/tools/scrape.py

EXPOSE 5000
ENV PATH="/home/jeopardy_data/app/venv/bin:$PATH"

CMD [ "python", "jeopardy_data/core.py", "api", "--file", "questions.db" ]