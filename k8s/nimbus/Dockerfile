FROM storm:latest

RUN mkdir /app

WORKDIR /app

COPY ./config/storm-nimbus.yaml /conf/storm.yaml

COPY storm-src-1.0-SNAPSHOT.jar /app/

CMD ["sh", "-c", "storm nimbus & storm ui"]