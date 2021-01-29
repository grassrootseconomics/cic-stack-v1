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
docker-compose up -d --no-deps --build <service_name>
```