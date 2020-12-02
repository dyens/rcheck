QUEUE_1 = 'sm_queue1'
QUEUE_2 = 'sm_queue2'
EXCHANGE = 'sm_exchange'

def setup(channel):
    channel.queue_declare(
        queue=QUEUE_1,
        durable=True, # Queue saved at rabbitmq reloading
        exclusive=False,
        auto_delete=False,
    )
    channel.queue_declare(
        queue=QUEUE_2,
        durable=True, # Queue saved at rabbitmq reloading
        exclusive=False,
        auto_delete=False,
    )

    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type='direct',
        durable=True,
    )

    channel.queue_bind(
        exchange=EXCHANGE,
        queue=QUEUE_1,
        routing_key=QUEUE_1,
    )

    channel.queue_bind(
        exchange=EXCHANGE,
        queue=QUEUE_2,
        routing_key=QUEUE_2,
    )
