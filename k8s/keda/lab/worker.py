import pika
import os
import time

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
QUEUE_NAME = os.getenv('QUEUE_NAME', 'task_queue')
RABBITMQ_USERNAME = os.getenv('RABBITMQ_USERNAME')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')
def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    ))

    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    print(f" [*] Waiting for messages in {QUEUE_NAME}. To exit press CTRL+C")

    def callback(ch, method, properties, body):
        print(f" [x] Received {body}")
        time.sleep(body.count(b'.'))  # Simulate work
        print(f" [x] Done")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    channel.start_consuming()

if __name__ == "__main__":
    main()
