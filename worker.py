import pika
import time
import json
import logging
from threading import Thread
from queue import Queue, Empty
from functools import partial

logger = logging.getLogger(__name__)

AMPQ_URL = 'amqp://127.0.0.1:5672'
QUEUE = 'calc_queue'
EXCHANGE = 'calc_exchange'

PQUEUE = 'publish_queue'
PEXCHANGE = 'publish_exchange'

MAX_WORKERS = 3


def do_work(msg):
    print('do_work', msg)
    time.sleep(20)
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
        print('ack message')
        if channel.is_open:
            channel.basic_ack(delivery_tag)
        else:
            # Channel is already closed, so we can't ACK this message;
            # log and/or do something that makes sense for your app in this case.
            raise RuntimeError('Channel is closed')

    def  _publish_result(self, channel, result):
        print('publish result')
        if channel.is_open:
            channel.basic_publish(
                exchange=PEXCHANGE,
                routing_key=PQUEUE,
                body = result,
                properties=pika.BasicProperties(delivery_mode=2), # Чтоб сообщение не терялось при рестарте приложения
            )
        else:
            # Channel is already closed, so we can't ACK this message;
            # log and/or do something that makes sense for your app in this case.
            raise RuntimeError('Channel is closed')


        

    def run(self):
        msg = self._body
        result = do_work(msg)
        self._connection.add_callback_threadsafe(
            partial(
                self._publish_result,
                self._channel, result,
            ),
        )
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
        self._setup_calc_queue()
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

    def _setup_calc_queue(self):
        self._channel.queue_declare(
            queue=QUEUE,
            durable=True, # Queue saved at rabbitmq reloading
            exclusive=False,
            auto_delete=False,
        )

        self._channel.exchange_declare(
            exchange=EXCHANGE,
            exchange_type='direct',
            durable=True,
        )

        self._channel.queue_bind(
            exchange=EXCHANGE,
            queue=QUEUE,
        #    routing_key=not needed for direct exchange,
        )

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
            queue=QUEUE,
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

#import sys
#sys.exit()
#
#
#
#
#class Worker(threading.Thread):
#    def __init__(self, ):
#        super().__init__()
#        self.rmq_parameters = pika.ConnectionParameters('127.0.0.1', 5672)
#        self.rmq_connection = pika.BlockingConnection(self.rmq_parameters)
#        self.rmq_channel = self.rmq_connection.channel()
#        # Rabbit просто отдает сообщения равномерно воркерам
#        # С данной настройкой он не передаст ворукеру message если тот еще не закончил
#        self.rmq_channel.basic_qos(prefetch_count=1)
#        self.rmq_channel.basic_consume(on_message_callback=self.on_message, queue=QUEUE)
#        self.config_publish_queue()
#
#
#    def config_publish_queue(self):
#        self.rmq_channel.queue_declare(
#            queue=PQUEUE,
#            durable=True, # Queue saved at rabbitmq reloading
#            exclusive=False,
#            auto_delete=False,
#        )
#
#        self.rmq_channel.exchange_declare(
#            exchange=PEXCHANGE,
#            exchange_type='direct',
#            durable=True,
#        )
#
#        self.rmq_channel.queue_bind(
#            exchange=PEXCHANGE,
#            queue=PQUEUE,
#        #    routing_key=not needed for direct exchange,
#        )
#
#
#
#    def on_message(self, channel, method_frame, header_frame, body):
#        msg = json.loads(body)
#        print(msg)
##        time.sleep(70)
#        print('Done')
#
#        msg = {
#            'msg': msg,
#            'done': True
#        }
#        self.rmq_channel.basic_publish(
#            exchange=PEXCHANGE,
#            routing_key=PQUEUE,
#            body = json.dumps(msg),
#            properties=pika.BasicProperties(delivery_mode=2), # Чтоб сообщение не терялось при рестарте приложения
#        )
#
#        channel.basic_ack(delivery_tag=method_frame.delivery_tag)
#
#
#
#    def run(self):
#        try:
#            self.rmq_channel.start_consuming()
#        except KeyboardInterrupt:
#            self.rmq_channel.stop_consuming()
#        except Exception as exc:
#            self.rmq_channel.stop_consuming()
#            logger.exception(exc)
#
#
#
#threads = []
#for _ in range(3):
#    thread = Worker()
#    thread.start()
#    threads.append(thread)
#
#for thread in threads:
#    thread.join()
