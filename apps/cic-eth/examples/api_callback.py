# standard imports
import logging
import uuid
import socket

# third-party imports
import celery
import redis

# local imports
import cic_eth

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

celery_app = celery.Celery(broker='redis://')

uu = uuid.uuid4()

r = redis.Redis()
r_key = '{}-results'.format(uu)

c = 3
results = []
for i in range(c):
    x = uuid.uuid4()
    results.append(str(x))


@celery_app.task(queue=str(uu), names='customcustom')
def custom_callback(result_from_chain, static_param_from_api, status_code_from_chain=0, message_from_chain={}):
    global c

    r.rpush(r_key, result_from_chain)
    l = r.llen(r_key)
    logg.debug('i {} l {} result {} url {} statuscode {} message {}'.format(
        i,
        l,
        result_from_chain,
        static_param_from_api,
        status_code_from_chain,
        message_from_chain,
        )
        )
    if l == c:
        r.delete(r_key)
        celery_app.control.broadcast('shutdown', destination=['{}@{}'.format(uu, socket.gethostname())])


@celery_app.task(queue=str(uu), name='dodorunrunrun')
def custom_run(results): 
    for z in results:
        logg.debug('sending {}'.format(z))
        a = cic_eth.Api(callback_param=uu, callback_task=custom_callback)
        a.ping(z)
      

if __name__ == '__main__':
    r.delete(r_key)
    s = celery.signature(
            'dodorunrunrun',
            [results],
            queue=str(uu),
            )
    s.apply_async()

    worker = celery_app.worker_main(
            [
                'api_callback',
                '--loglevel=DEBUG',
                '-n',
                '{}@%h'.format(uu),
                '-Q',
                str(uu),
                ],
            )
