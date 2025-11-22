"""
Social Text Producer Service
Generates mock social media posts with varying sentiment and publishes to Kafka.
"""
import os
import sys
import time
import random
import logging
from datetime import datetime
from faker import Faker
from prometheus_client import Counter, start_http_server

# Add shared module to path
sys.path.append('/app/shared')
from kafka_config import create_producer, produce_message, create_topics_if_not_exist
from models import SocialText

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
messages_sent = Counter('social_producer_messages_sent_total', 'Total messages sent to Kafka')

# Initialize Faker
fake = Faker()


class SocialProducer:
    """Generates and publishes mock social media posts."""
    
    # Sentiment-based text templates
    POSITIVE_TEMPLATES = [
        "Just had an amazing experience with {}! Highly recommend! 🎉",
        "Absolutely love {}! Best decision ever! ❤️",
        "Wow, {} exceeded all my expectations! So happy! 😊",
        "Can't stop thinking about how great {} is! #blessed",
        "{} is fantastic! Everyone should try it! 🌟",
        "Having the best time with {}! Life is good! ☀️"
    ]
    
    NEGATIVE_TEMPLATES = [
        "Really disappointed with {}. Not what I expected. 😞",
        "Terrible experience with {}. Would not recommend. 👎",
        "{} was a complete waste of time and money. Frustrated! 😤",
        "Avoid {} at all costs. So many issues! ⚠️",
        "Regret trying {}. Such a letdown. 😔",
        "Why is {} so bad? Expected much better. Disappointed."
    ]
    
    NEUTRAL_TEMPLATES = [
        "Just tried {}. It's okay, nothing special.",
        "Spent some time with {} today. Average experience.",
        "{} is decent. Could be better, could be worse.",
        "Checking out {}. Seems alright so far.",
        "Using {} for the first time. We'll see how it goes.",
        "Got {} today. Pretty standard, I guess."
    ]
    
    PLATFORMS = ['twitter', 'facebook', 'instagram', 'linkedin', 'reddit', 'tiktok']
    
    HASHTAGS = [
        ['#tech', '#innovation'],
        ['#lifestyle', '#wellness'],
        ['#food', '#foodie'],
        ['#travel', '#adventure'],
        ['#fitness', '#health'],
        ['#business', '#entrepreneur'],
        ['#entertainment', '#movies'],
        ['#gaming', '#esports']
    ]
    
    def __init__(self):
        self.producer = create_producer()
        self.topic = os.getenv('KAFKA_TOPIC_SOCIAL', 'social-text')
        self.interval = float(os.getenv('SOCIAL_INTERVAL', '2'))
        
        # Create topic if it doesn't exist
        create_topics_if_not_exist([self.topic])
        
        logger.info(f"SocialProducer initialized - Topic: {self.topic}, Interval: {self.interval}s")
    
    def generate_post(self) -> SocialText:
        """Generate a random social media post."""
        # Randomly select sentiment distribution (60% positive, 20% negative, 20% neutral)
        sentiment_choice = random.choices(
            ['positive', 'negative', 'neutral'],
            weights=[0.6, 0.2, 0.2]
        )[0]
        
        # Select template based on sentiment
        if sentiment_choice == 'positive':
            template = random.choice(self.POSITIVE_TEMPLATES)
        elif sentiment_choice == 'negative':
            template = random.choice(self.NEGATIVE_TEMPLATES)
        else:
            template = random.choice(self.NEUTRAL_TEMPLATES)
        
        # Generate subject
        subjects = [
            fake.company(),
            fake.catch_phrase(),
            f"the new {fake.word()}",
            fake.bs().title(),
            f"{fake.word().title()} {random.choice(['App', 'Service', 'Product', 'Platform'])}"
        ]
        subject = random.choice(subjects)
        
        # Create post text
        text = template.format(subject)
        
        # Generate post
        post = SocialText(
            text=text,
            user_id=fake.user_name(),
            platform=random.choice(self.PLATFORMS),
            hashtags=random.choice(self.HASHTAGS),
            metadata={
                'expected_sentiment': sentiment_choice,  # For validation
                'location': fake.city(),
                'language': 'en'
            }
        )
        
        return post
    
    def run(self):
        """Main loop to generate and publish social posts."""
        logger.info("Starting social text generation...")
        
        try:
            while True:
                # Generate post
                post = self.generate_post()
                
                # Publish to Kafka
                produce_message(
                    self.producer,
                    self.topic,
                    post.model_dump(),
                    key=post.user_id
                )
                messages_sent.inc()
                
                logger.info(f"Published post from {post.user_id} on {post.platform}: {post.text[:50]}...")
                
                # Flush producer
                self.producer.flush()
                
                # Wait for next interval
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            logger.info("Shutting down social producer...")
        finally:
            self.producer.flush()
            logger.info("Social producer stopped")


if __name__ == '__main__':
    # Start Prometheus metrics server
    prometheus_port = 8002
    start_http_server(prometheus_port)
    logger.info(f"Prometheus metrics available at http://0.0.0.0:{prometheus_port}/metrics")
    
    # Start producer
    producer = SocialProducer()
    producer.run()
