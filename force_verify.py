import os
from dotenv import load_dotenv
import tweepy

# Force override with .env content
load_dotenv(override=True)

def clean(v):
    if not v: return ""
    return v.strip("'").strip('"').strip()

ck = clean(os.getenv('TWITTER_CONSUMER_KEY'))
cs = clean(os.getenv('TWITTER_CONSUMER_SECRET'))
at = clean(os.getenv('TWITTER_ACCESS_TOKEN'))
ats = clean(os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))

print(f"FORCING VERIFICATION WITH NEW KEYS (Starts with: {ck[:4]})")

try:
    client = tweepy.Client(
        consumer_key=ck, consumer_secret=cs,
        access_token=at, access_token_secret=ats
    )
    me = client.get_me()
    if me.data:
        print(f"VERIFICATION_SUCCESS: Authenticated as @{me.data.username}")
        
        # Immediate Broadcast of CVA-001
        text = "CROW AUDIT CVA-001: 6.75% decline in Sundarbans Blue Carbon density detected (2017-2026). Spectral truth reconciled. #CrowAudit #ClimateTruth"
        response = client.create_tweet(text=text)
        print(f"BROADCAST_SUCCESS: Tweet ID {response.data['id']}")
    else:
        print("VERIFICATION_FAILED: No data returned.")
except Exception as e:
    print(f"VERIFICATION_ERROR: {e}")

