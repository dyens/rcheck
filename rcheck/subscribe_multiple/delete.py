"""
Delete queues.
"""

import pika

parameters = pika.ConnectionParameters(
    '127.0.0.1',
    5672,
    heartbeat=5,
)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()


for customer in range(10):
    channel.queue_delete('sm_queue_%s' % str(customer))

