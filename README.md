# cic-internal-integration

## Getting started 

start cluster
```
docker-compose up
```

stop cluster
```
docker-compose down
```

delete data
```
docker-compose down -v
```

rebuild an images
```
docker-compose up --build <service_name>
``

Deployment variables are writtend to service-configs/.env after everthing is up.`
