import pika
import time
import json

AMPQ_URL = 'amqp://127.0.0.1:5672'
QUEUE = 'calc_queue'
EXCHANGE = 'calc_exchange'

rmq_parameters = pika.ConnectionParameters('127.0.0.1', 5672)
rmq_connection = pika.BlockingConnection(rmq_parameters)
rmq_channel = rmq_connection.channel()

models = ['ModelA', 'ModelB', 'ModelC']


# Config queue and exchange

rmq_channel.queue_declare(
    queue=QUEUE,
    durable=True, # Queue saved at rabbitmq reloading
    exclusive=False,
    auto_delete=False,
)

rmq_channel.exchange_declare(
    exchange=EXCHANGE,
    exchange_type='direct',
    durable=True,
)

rmq_channel.queue_bind(
    exchange=EXCHANGE,
    queue=QUEUE,
#    routing_key=not needed for direct exchange,
)


job_n = 0
for model in models:
    for _ in range(1000):
        job_n += 1
        msg = {
            'model': model,
            'job': job_n,
        }
        rmq_channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=QUEUE,
            body = json.dumps(msg),
            properties=pika.BasicProperties(delivery_mode=2), # Чтоб сообщение не терялось при рестарте приложения
        )
        print(msg)
        time.sleep(0.5)
