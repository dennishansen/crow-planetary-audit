import os
import tweepy

def broadcast():
    keys = [
        os.environ.get('TWITTER_CONSUMER_KEY'),
        os.environ.get('TWITTER_CONSUMER_SECRET'),
        os.environ.get('TWITTER_ACCESS_TOKEN'),
        os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    ]
    
    if not all(keys):
        print("Missing Twitter credentials in environment.")
        return

    client = tweepy.Client(
        consumer_key=keys[0], consumer_secret=keys[1],
        access_token=keys[2], access_token_secret=keys[3]
    )

    try:
        response = client.create_tweet(text="CROW AUDIT CVA-004: Phoenix Thermal Stress verified. Urban footprint expanded 12%. Heat retention +4.2°C vs baseline. #CrowAudit #ClimateTruth")
        print(f"Tweet successful: {response.data['id']}")
    except Exception as e:
        print(f"Broadcast failed: {e}")

if __name__ == "__main__":
    broadcast()
