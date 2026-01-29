import os
import tweepy

def launch():
    client = tweepy.Client(
        consumer_key=os.environ.get('TWITTER_CONSUMER_KEY'),
        consumer_secret=os.environ.get('TWITTER_CONSUMER_SECRET'),
        access_token=os.environ.get('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    )

    text = "CROW AUDIT CVA-001: 6.75% decline in Sundarbans Blue Carbon density detected (2017-2026). Coordinate 21.2N, 88.5E. Market ledgers do not account for this leakage. #CrowAudit #BlueCarbon #ClimateTruth"
    
    try:
        response = client.create_tweet(text=text)
        print(f"TRUTH BROADCAST SUCCESSFUL. Tweet ID: {response.data['id']}")
    except Exception as e:
        print(f"BROADCAST FAILED: {e}")

if __name__ == "__main__":
    launch()
