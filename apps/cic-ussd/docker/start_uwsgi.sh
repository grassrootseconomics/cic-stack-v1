#!/bin/bash

. ./db.sh

/usr/local/bin/uwsgi --wsgi-file /usr/local/lib/python3.8/site-packages/cic_ussd/runnable/server.py --http :80 --pyargv "-vv"