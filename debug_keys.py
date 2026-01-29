import os
import tweepy

keys = [
    'TWITTER_CONSUMER_KEY',
    'TWITTER_CONSUMER_SECRET',
    'TWITTER_ACCESS_TOKEN',
    'TWITTER_ACCESS_TOKEN_SECRET'
]

for k in keys:
    val = os.environ.get(k)
    print(f"{k}: {'PRESENT' if val else 'MISSING'} (Length: {len(val) if val else 0})")

auth = tweepy.OAuth1UserHandler(
    os.environ.get('TWITTER_CONSUMER_KEY'),
    os.environ.get('TWITTER_CONSUMER_SECRET'),
    os.environ.get('TWITTER_ACCESS_TOKEN'),
    os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
)
api = tweepy.API(auth)

try:
    user = api.verify_credentials()
    print(f"OAUTH1_SUCCESS: {user.screen_name}")
except Exception as e:
    print(f"OAUTH1_ERROR: {e}")
