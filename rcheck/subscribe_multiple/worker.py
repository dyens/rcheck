import pika
import time
import json
import logging
from threading import Thread
from queue import Queue, Empty
from functools import partial
from setup import setup, QUEUE_1, QUEUE_2, EXCHANGE

logger = logging.getLogger(__name__)

MAX_WORKERS = 2


def do_work(msg):
    print('do_work', msg)
    time.sleep(2)
    print('do_work', 'done', msg)
    return msg
    


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
            # Channel is already closed, so we can't ACK this message;
            # log and/or do something that makes sense for your app in this case.
            raise RuntimeError('Channel is closed')


    def run(self):
        msg = self._body
        result = do_work(msg)
        self._connection.add_callback_threadsafe(
            partial(
                self._ack_message,
                self._channel, self._delivery_tag,
            ),
        )
        

class Consumer:
    def __init__(self):
        super().__init__()
        self._setup_channel()
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
        self._channel.basic_qos(prefetch_count=MAX_WORKERS, global_qos=True)

        self._channel.basic_consume(
            on_message_callback=partial(self._on_message, connection=self._connection),
            queue=QUEUE_1,
        )
        self._channel.basic_consume(
            on_message_callback=partial(self._on_message, connection=self._connection),
            queue=QUEUE_2,
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
