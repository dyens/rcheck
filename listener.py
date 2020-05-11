import pika
import time
import json
from queue import Queue, Empty
from threading import Thread

QUEUE = 'calc_queue'
EXCHANGE = 'calc_exchange'
QUEUE_SIZE = 5


class Pusher(Thread):
    def __init__(self, queue):
        super().__init__()
        self._queue = queue
        self._setup_channel()
        self._setup_calc_queue()

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


    def _retry(self, fn, *args, **kwargs):
        while True:
            try:
                return fn(*args, **kwargs)
            except pika.exceptions.AMQPError:
                time.sleep(2)
                self._setup_channel()
                continue

    def _heartbeat(self):
        self._connection.process_data_events()

    def _publish(self, msg):
        self._channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=QUEUE,
                body = json.dumps(msg),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        print('published', msg)

    def run(self):
        print('Pusher started')
        while True:
            msg = None
            try:
                msg = self._queue.get(timeout=2)
                print('get from queue', msg)
            except Empty:
                self._retry(self._heartbeat)
                continue

            self._retry(self._publish, msg)
            self._queue.task_done()



            

class Producer:
    def __init__(self, queue):
        super().__init__()
        self._queue = queue

    def run(self):
        time.sleep(3)
        print('Start publish')
        for i in range(10):
            time.sleep(5)
            print('add to queue', i)
            self._queue.put(i)
        # Important: this is required for sync queue
        self._queue.join()

 


queue = Queue(maxsize=QUEUE_SIZE)
pusher = Pusher(queue)
pusher.daemon = True
pusher.start()

producer = Producer(queue)
producer.run()
