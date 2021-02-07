# local imports
import cic_notify

# third-part imports
import celery


# TODO: Add configurable backend
celery_app = celery.Celery(broker='redis:///', backend='redis:///')

api = cic_notify.Api('cic-notify')
print(api.sms('+25412121212', 'foo'))
