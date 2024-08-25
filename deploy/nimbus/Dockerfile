FROM storm:latest

RUN mkdir /app

WORKDIR /app

COPY ./config/storm-nimbus.yaml /conf/storm.yaml

EXPOSE 6627 8081

CMD ["sh", "-c", "storm nimbus & storm ui"]
