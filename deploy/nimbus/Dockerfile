FROM storm:latest

RUN mkdir /app

WORKDIR /app

COPY ./config/storm-nimbus.yaml /conf/storm.yaml


CMD ["sh", "-c", "storm nimbus & storm ui"]