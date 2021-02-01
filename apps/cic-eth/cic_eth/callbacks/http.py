# standard imports
import json
import ssl
import os
import urllib
from urllib import request
from urllib.request import urlopen

# third-party imports
from . import Callback
import celery

celery_app = celery.current_app
logg = celery_app.log.get_default_logger()


@celery_app.task(base=Callback, bind=True)
def http(self, result, url, status_code):
    """A generic web callback implementation for task results.

    Input parameters depend on whether the callback is used as an error callback, or as a part of a celery chain.

    The callback receives:

    {
        'root_id': the uuid of the topmost task in the chain, which is known to the API caller.
        'status': <status_code>,
        'result': <result>,
    }

    :param result: Task context object (on error) or return value of previous task (on success)
    :type result: Varies
    :param url: Url to HTTP POST results to
    :type url: str
    :param status_code: 0 on success, any other value is error
    :type status_code: int
    """
    req = request.Request(url)
    data = {
            'root_id': self.request.root_id,
            'status': status_code,
            'result': result,
            }
    data_str = json.dumps(data)
    data_bytes = data_str.encode('utf-8')
    req.add_header('Content-Type', 'application/json')
    req.data = data_bytes

    ctx = None
    if self.ssl:
        ctx = ssl.SSLContext()
        ctx.load_cert_chain(
            self.ssl_cert_file,
            self.ssl_key_file,
            self.ssl_password,
            )

    response = urlopen(
            req,
            context=ctx,
            )

    if response.status != 200:
        raise RuntimeError('Expected status 200 from remote server, but got {} {}'.format(response.status, response.msg))
