#!/bin/bash

PGPASSWORD=$DATABASE_PASSWORD psql -U $DATABASE_USER -h $DATABASE_HOST -p $DATABASE_PORT -d $DATABASE_NAME /usr/local/share/cic-meta/sql/server.sql
