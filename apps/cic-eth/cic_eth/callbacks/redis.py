# standard imports
import logging
import json
import redis as redis_interface

# third-party imports
import celery

# local imports
from . import Callback

celery_app = celery.current_app

logg = celery_app.log.get_default_logger()


@celery_app.task(base=Callback, bind=True)
def redis(self, result, destination, status_code):
    (host, port, db, channel) = destination.split(':')
    r = redis_interface.Redis(host=host, port=port, db=db)
    s = json.dumps(result)
    logg.debug('redis callback on host {} port {} db {} channel {}'.format(host, port, db, channel))
    r.publish(channel, s)
    r.close()
