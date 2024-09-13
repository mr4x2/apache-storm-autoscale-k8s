FROM storm:2.6.2

RUN mkdir /app

WORKDIR /app

COPY ./config/storm-supervisor.yaml /conf/storm.yaml

EXPOSE 6700-6703

CMD ["storm", "supervisor"]
