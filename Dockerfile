FROM python:3.10-slim-bullseye as base

FROM base as builder

COPY requirements.txt /requirements.txt

RUN apt-get update && apt-get install gcc libssl-dev -y && apt-get clean
RUN pip install --user -r /requirements.txt

FROM base

COPY --from=builder /root/.local /root/.local

WORKDIR /hn-filter
COPY src src
COPY config config

EXPOSE 9090

ENV APP_PORT=9090

CMD ["python", "-u", "src/filter/server.py", "--configpath", "/hn-filter/config"]
