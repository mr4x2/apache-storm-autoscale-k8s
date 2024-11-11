import pika

RABBITMQ_HOST = "rabbitmq.rabbitmq.svc.cluster.local"
QUEUE_NAME = "task_queue"

RABBITMQ_USERNAME = os.getenv('RABBITMQ_USERNAME')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    ))
channel = connection.channel()

channel.queue_declare(queue=QUEUE_NAME, durable=True)

for i in range(50):
    message = f"Task {i}"
    channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=message)
    print(f" [x] Sent {message}")
connection.close()
