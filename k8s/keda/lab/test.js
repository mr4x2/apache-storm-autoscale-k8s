const amqp = require('amqplib');

const queue = 'task_queue';

async function sendMessages() {
    const connection = await amqp.connect("amqp://user:oYOGgoxLQwFN4EiK@rabbitmq.rabbitmq.svc.cluster.local");
    const channel = await connection.createChannel();
    await channel.assertQueue(queue, { durable: true });

    for (let i = 0; i < 50; i++) {
        channel.sendToQueue(queue, Buffer.from(`Message ${i}`));
        console.log(`Sent message ${i}`);
    }

    setTimeout(() => {
        connection.close();
    }, 500);
}

sendMessages().catch(console.error);