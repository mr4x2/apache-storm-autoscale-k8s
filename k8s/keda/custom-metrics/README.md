### How to run keda controller

```cmd
docker build -t mr4x2/keda-controller:v1 .
docker push mr4x2/keda-controller:v1
```

```cmd
cp sample.env .env
```

```cmd
docker run -d -p 8001:8001 --env-file .env --name keda-controller mr4x2/keda-controller:v1
```