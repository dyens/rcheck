import pika
import time
import json
import logging
import threading

logger = logging.getLogger(__name__)

AMPQ_URL = 'amqp://127.0.0.1:5672'
QUEUE = 'calc_queue'

PQUEUE = 'publish_queue'

def on_message(channel, method_frame, header_frame, body):
    msg = json.loads(body)
    print(msg)
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)


rmq_parameters = pika.ConnectionParameters('127.0.0.1', 5672)
rmq_connection = pika.BlockingConnection(rmq_parameters)
rmq_channel = rmq_connection.channel()

rmq_channel.basic_qos(prefetch_count=1)
rmq_channel.basic_consume(on_message_callback=on_message, queue=PQUEUE)


try:
    rmq_channel.start_consuming()
except KeyboardInterrupt:
    rmq_channel.stop_consuming()
except Exception as exc:
    rmq_channel.stop_consuming()
    logger.exception(exc)

