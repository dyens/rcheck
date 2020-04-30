import pika
import time
import json
import logging
import threading

logger = logging.getLogger(__name__)

AMPQ_URL = 'amqp://127.0.0.1:5672'
QUEUE = 'calc_queue'

PQUEUE = 'publish_queue'
PEXCHANGE = 'publish_exchange'


class Worker(threading.Thread):
    def __init__(self, ):
        super().__init__()
        self.rmq_parameters = pika.ConnectionParameters('127.0.0.1', 5672)
        self.rmq_connection = pika.BlockingConnection(self.rmq_parameters)
        self.rmq_channel = self.rmq_connection.channel()
        # Rabbit просто отдает сообщения равномерно воркерам
        # С данной настройкой он не передаст ворукеру message если тот еще не закончил
        self.rmq_channel.basic_qos(prefetch_count=1)
        self.rmq_channel.basic_consume(on_message_callback=self.on_message, queue=QUEUE)
        self.config_publish_queue()


    def config_publish_queue(self):
        self.rmq_channel.queue_declare(
            queue=PQUEUE,
            durable=True, # Queue saved at rabbitmq reloading
            exclusive=False,
            auto_delete=False,
        )

        self.rmq_channel.exchange_declare(
            exchange=PEXCHANGE,
            exchange_type='direct',
            durable=True,
        )

        self.rmq_channel.queue_bind(
            exchange=PEXCHANGE,
            queue=PQUEUE,
        #    routing_key=not needed for direct exchange,
        )



    def on_message(self, channel, method_frame, header_frame, body):
        msg = json.loads(body)
        print(msg)
        time.sleep(5)
        print('Done')

        msg['done'] = True
        self.rmq_channel.basic_publish(
            exchange=PEXCHANGE,
            routing_key=PQUEUE,
            body = json.dumps(msg),
            properties=pika.BasicProperties(delivery_mode=2), # Чтоб сообщение не терялось при рестарте приложения
        )

        channel.basic_ack(delivery_tag=method_frame.delivery_tag)



    def run(self):
        try:
            self.rmq_channel.start_consuming()
        except KeyboardInterrupt:
            self.rmq_channel.stop_consuming()
        except Exception as exc:
            self.rmq_channel.stop_consuming()
            logger.exception(exc)



threads = []
for _ in range(3):
    thread = Worker()
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()
