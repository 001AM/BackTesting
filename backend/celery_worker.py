from celery import Celery
from kombu import Queue

celery_app = Celery('app',include=["app.task"],)

# celery_app.conf.update(
#     broker_url='redis://localhost:6379/0',
#     result_backend='redis://localhost:6379/0',
#     task_serializer='json',
#     accept_content=['json'],
#     result_serializer='json',
#     timezone='UTC',
#     enable_utc=True,
#     task_routes={
#         'app.task.create_trace_async': {'queue': 'traces'},
#         'app.task.update_trace_completion_async': {'queue': 'traces'},
#         'app.task.update_trace_error_async': {'queue': 'traces'},
#         'app.task.create_observation_async': {'queue': 'observations'},
#         'app.task.add_trace_score_async': {'queue': 'scores'},
#     },
#     task_default_queue='default',
#     task_queues=(
#         Queue('default'),
#         Queue('traces'),
#         Queue('observations'),
#         Queue('scores'),
#     ),
#     worker_prefetch_multiplier=1,
#     task_acks_late=True,
# )
