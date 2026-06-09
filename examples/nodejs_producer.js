/**
 * Example: send custom metrics to MetricWatch from Node.js.
 *
 * Prerequisites:
 *   npm install kafkajs
 *
 * With MetricWatch running:
 *   KAFKA_BOOTSTRAP_SERVERS=localhost:29092 node examples/nodejs_producer.js
 */
const { Kafka } = require('kafkajs');
const os = require('os');

const bootstrap = process.env.KAFKA_BOOTSTRAP_SERVERS || 'localhost:29092';
const topic = process.env.KAFKA_TOPIC_METRICS || 'system-metrics';
const hostname = process.env.METRIC_HOSTNAME || os.hostname();

async function main() {
  const kafka = new Kafka({ clientId: 'metricwatch-example', brokers: [bootstrap] });
  const producer = kafka.producer();
  await producer.connect();

  for (let i = 0; i < 20; i++) {
    const payload = {
      metric_type: 'custom',
      value: 30 + Math.random() * 20,
      hostname,
      timestamp: new Date().toISOString(),
      metadata: { source: 'nodejs_producer', iteration: i },
    };
    await producer.send({
      topic,
      messages: [{ key: `${hostname}:custom`, value: JSON.stringify(payload) }],
    });
    console.log(`Sent metric ${i}: ${payload.value.toFixed(2)}`);
    await new Promise((r) => setTimeout(r, 2000));
  }

  await producer.disconnect();
  console.log('Done.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
