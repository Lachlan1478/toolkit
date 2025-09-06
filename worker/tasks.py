import os
from celery import Celery

CELERY_BROKER = os.getenv("REDIS_URL", "redis://redis:6379/0")
app = Celery("toolkit", broker=CELERY_BROKER, backend=CELERY_BROKER)

@app.task
def noop(x=1):
    return x + 1
