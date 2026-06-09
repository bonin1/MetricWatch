"""
System Metrics Producer Service
Collects CPU, memory, disk, and network metrics and publishes to Kafka.
"""
import os
import sys
import time
import socket
import logging
import psutil
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server

# Add shared module to path
sys.path.append('/app/shared')
from kafka_config import create_producer, produce_message, create_topics_if_not_exist
from models import SystemMetric

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
messages_sent = Counter('metrics_producer_messages_sent_total', 'Total messages sent to Kafka')
cpu_usage = Gauge('system_cpu_percent', 'CPU usage percentage')
memory_usage = Gauge('system_memory_percent', 'Memory usage percentage')
disk_usage = Gauge('system_disk_percent', 'Disk usage percentage')


class MetricsProducer:
    """Collects and publishes system metrics."""
    
    def __init__(self):
        self.producer = create_producer()
        self.topic = os.getenv('KAFKA_TOPIC_METRICS', 'system-metrics')
        self.interval = int(os.getenv('METRICS_INTERVAL', '5'))
        self.hostname = socket.gethostname()
        
        # Create topic if it doesn't exist
        create_topics_if_not_exist([self.topic])
        
        logger.info(f"MetricsProducer initialized - Topic: {self.topic}, Interval: {self.interval}s")
    
    def collect_cpu_metrics(self) -> SystemMetric:
        """Collect CPU usage metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_usage.set(cpu_percent)
        
        return SystemMetric(
            metric_type='cpu',
            value=cpu_percent,
            hostname=self.hostname,
            metadata={
                'cpu_count': psutil.cpu_count(),
                'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
        )
    
    def collect_memory_metrics(self) -> SystemMetric:
        """Collect memory usage metrics."""
        mem = psutil.virtual_memory()
        memory_usage.set(mem.percent)
        
        return SystemMetric(
            metric_type='memory',
            value=mem.percent,
            hostname=self.hostname,
            metadata={
                'total_gb': round(mem.total / (1024**3), 2),
                'available_gb': round(mem.available / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2)
            }
        )
    
    def collect_disk_metrics(self) -> SystemMetric:
        """Collect disk usage metrics."""
        disk = psutil.disk_usage('/')
        disk_usage.set(disk.percent)
        
        return SystemMetric(
            metric_type='disk',
            value=disk.percent,
            hostname=self.hostname,
            metadata={
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2)
            }
        )
    
    def collect_network_metrics(self) -> SystemMetric:
        """Collect network I/O metrics."""
        net_io = psutil.net_io_counters()
        
        # Calculate throughput (bytes per second)
        if not hasattr(self, '_last_net_io'):
            self._last_net_io = net_io
            self._last_net_time = time.time()
            return None
        
        time_delta = time.time() - self._last_net_time
        bytes_sent_per_sec = (net_io.bytes_sent - self._last_net_io.bytes_sent) / time_delta
        bytes_recv_per_sec = (net_io.bytes_recv - self._last_net_io.bytes_recv) / time_delta
        
        self._last_net_io = net_io
        self._last_net_time = time.time()
        
        # Use combined throughput as value
        total_throughput_mbps = (bytes_sent_per_sec + bytes_recv_per_sec) / (1024**2)
        
        return SystemMetric(
            metric_type='network',
            value=total_throughput_mbps,
            hostname=self.hostname,
            metadata={
                'bytes_sent_per_sec': round(bytes_sent_per_sec, 2),
                'bytes_recv_per_sec': round(bytes_recv_per_sec, 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        )
    
    def run(self):
        """Main loop to collect and publish metrics."""
        logger.info("Starting metrics collection...")
        
        try:
            while True:
                # Collect all metrics
                metrics = [
                    self.collect_cpu_metrics(),
                    self.collect_memory_metrics(),
                    self.collect_disk_metrics(),
                    self.collect_network_metrics()
                ]
                
                # Publish to Kafka
                for metric in metrics:
                    if metric:  # Skip None values (first network metric)
                        produce_message(
                            self.producer,
                            self.topic,
                            metric.model_dump(mode='json'),
                            key=f"{self.hostname}:{metric.metric_type}"
                        )
                        messages_sent.inc()
                        logger.debug(f"Published {metric.metric_type} metric: {metric.value}")
                
                # Flush producer
                self.producer.flush()
                
                # Wait for next interval
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            logger.info("Shutting down metrics producer...")
        finally:
            self.producer.flush()
            logger.info("Metrics producer stopped")


if __name__ == '__main__':
    # Start Prometheus metrics server
    prometheus_port = 8001
    start_http_server(prometheus_port)
    logger.info(f"Prometheus metrics available at http://0.0.0.0:{prometheus_port}/metrics")
    
    # Start producer
    producer = MetricsProducer()
    producer.run()
