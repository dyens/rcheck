import pika
import time
import json
import logging
from threading import Thread
from queue import Queue, Empty
from functools import partial

logger = logging.getLogger(__name__)

AMPQ_URL = 'amqp://127.0.0.1:5672'

PQUEUE = 'publish_queue'
PEXCHANGE = 'publish_exchange'

MAX_WORKERS = 1


def do_work(msg):
    print(msg)
#    time.sleep(5)
    print('done')
    


class DoWork(Thread):
    def __init__(self, connection, channel, delivery_tag, body):
        super().__init__()
        self._connection = connection
        self._channel = channel
        self._delivery_tag = delivery_tag
        self._body = body

    def _ack_message(self, channel, delivery_tag):
        """Note that `channel` must be the same pika channel instance via which
        the message being ACKed was retrieved (AMQP protocol constraint).
        """
        if channel.is_open:
            channel.basic_ack(delivery_tag)
        else:
            raise RuntimeError('Channel is closed')
            # Channel is already closed, so we can't ACK this message;
            # log and/or do something that makes sense for your app in this case.
            pass

    def run(self):
        msg = self._body
        do_work(msg)
        self._connection.add_callback_threadsafe(
            partial(self._ack_message, self._channel, self._delivery_tag),
        )
        

class Consumer:
    def __init__(self):
        super().__init__()
        self._setup_channel()
        self._setup_publish_queue()
        self._setup_worker()
        self._threads = []

    def _setup_connection(self):
        self._parameters = pika.ConnectionParameters('127.0.0.1', 5672, heartbeat=5)
        while True:
            try:
                self._connection = pika.BlockingConnection(self._parameters)
                return
            except pika.exceptions.AMQPConnectionError:
                print('Not connection to Rabbitmq')
                time.sleep(2)
                continue


    def _setup_channel(self):
        self._setup_connection()
        self._channel = self._connection.channel()

    def _setup_publish_queue(self):
        self._channel.queue_declare(
            queue=PQUEUE,
            durable=True, # Queue saved at rabbitmq reloading
            exclusive=False,
            auto_delete=False,
        )

        self._channel.exchange_declare(
            exchange=PEXCHANGE,
            exchange_type='direct',
            durable=True,
        )

        self._channel.queue_bind(
            exchange=PEXCHANGE,
            queue=PQUEUE,
        #    routing_key=not needed for direct exchange,
        )


    def _on_message(self, channel, method_frame, header_frame, body, connection):
        delivery_tag = method_frame.delivery_tag
        thread = DoWork(
            self._connection, 
            self._channel, 
            delivery_tag, 
            body,
        )
        # We drop thread if rabbit is broken
        thread.daemon = True
        thread.start()
        self._threads.append(thread)

    def _setup_worker(self):
        self._channel.basic_qos(prefetch_count=MAX_WORKERS)
        self._channel.basic_consume(
            on_message_callback=partial(self._on_message, connection=self._connection),
            queue=PQUEUE,
        )



    def run(self):
        print('Start consumer')
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self._channel.stop_consuming()
        except Exception as exc:
            self._channel.stop_consuming()
            logger.exception(exc)


c = Consumer()
c.run()
