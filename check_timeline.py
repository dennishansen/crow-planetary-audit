import os
import tweepy

def run():
    keys = [
        os.environ.get('TWITTER_CONSUMER_KEY'),
        os.environ.get('TWITTER_CONSUMER_SECRET'),
        os.environ.get('TWITTER_ACCESS_TOKEN'),
        os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    ]
    if not all(keys): return
    client = tweepy.Client(bearer_token=os.environ.get('TWITTER_BEARER_TOKEN'))
    # If bearer token not set, use OAuth 1.0a
    auth = tweepy.OAuth1UserHandler(keys[0], keys[1], keys[2], keys[3])
    api = tweepy.API(auth)
    
    try:
        user = api.verify_credentials()
        print(f"Checking timeline for: {user.screen_name}")
        tweets = api.user_timeline(count=5)
        for t in tweets:
            print(f"ID: {t.id} | TEXT: {t.text[:50]}...")
    except Exception as e:
        print(f"FAILED_TO_READ_TIMELINE: {e}")

if __name__ == "__main__":
    run()
