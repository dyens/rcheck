
QUEUES_NUMBER = 1000
QUEUES = ['sm_queue_%s' % i for i in range(QUEUES_NUMBER)]
EXCHANGE = 'sm_exchange'

def setup(channel):
    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type='direct',
        durable=True,
    )

    for queue in QUEUES:
        channel.queue_declare(
            queue=queue,
            durable=True, # Queue saved at rabbitmq reloading
            exclusive=False,
            auto_delete=False,
        )

        channel.queue_bind(
            exchange=EXCHANGE,
            queue=queue,
            routing_key=queue,
        )
