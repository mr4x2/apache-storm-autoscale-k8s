const amqp = require('amqplib');

const queue = 'task_queue';

async function processMessages() {
    const connection = await amqp.connect(process.env.RABBITMQ_URL);
    const channel = await connection.createChannel();
    await channel.assertQueue(queue, { durable: true });

    console.log(`Worker is waiting for messages in ${queue}.`);
    channel.consume(queue, (msg) => {
        if (msg !== null) {
            console.log(`Processing message: ${msg.content.toString()}`);
            setTimeout(() => {
                channel.ack(msg);
            }, 1000); // Simulate processing time
        }
    });
}

processMessages().catch(console.error);
