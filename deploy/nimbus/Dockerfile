FROM storm:2.6.2

RUN mkdir /app

WORKDIR /app

COPY ./config/storm-nimbus.yaml /conf/storm.yaml

EXPOSE 6627 8081

CMD ["sh", "-c", "storm nimbus & storm ui"]
