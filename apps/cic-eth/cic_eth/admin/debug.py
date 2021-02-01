import datetime

import celery

celery_app = celery.current_app


@celery_app.task()
def out_tmp(tag, txt):
    f = open('/tmp/err.{}.txt'.format(tag), "w")
    f.write(txt)
    f.close()
