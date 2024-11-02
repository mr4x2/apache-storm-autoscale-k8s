## MQTT broker tutorial

### Run MQTT broker

Step 1: Build docker image
```cmd
docker build -t mqtt-broker .
```

Step 2: Push image to docker hub
```cmd
docker tag mqtt-broker mr4x2/mqtt-broker

docker push mr4x2/mqtt-broker
```

So you can use my image in k8s environment

Step 3: Run a docker container
```cmd
docker run -d -p 1883:1883 --name mqtt mqtt-broker
```

