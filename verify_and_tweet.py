import os
import tweepy
from dotenv import load_dotenv

def clean(v):
    if not v: return ""
    return v.strip("'").strip('"').strip()

def run():
    load_dotenv()
    
    ck = clean(os.getenv('TWITTER_CONSUMER_KEY'))
    cs = clean(os.getenv('TWITTER_CONSUMER_SECRET'))
    at = clean(os.getenv('TWITTER_ACCESS_TOKEN'))
    ats = clean(os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))

    print(f"DEBUG: CK_LEN={len(ck)}, CS_LEN={len(cs)}, AT_LEN={len(at)}, ATS_LEN={len(ats)}")

    try:
        client = tweepy.Client(
            consumer_key=ck, consumer_secret=cs,
            access_token=at, access_token_secret=ats
        )
        
        # Verify 
        me = client.get_me()
        if not me or not me.data:
            print("VERIFY_FAILED: No data returned from get_me")
            return

        print(f"VERIFY_SUCCESS: {me.data.username}")
        
        # Attempt Tweet
        text = "CROW AUDIT CVA-001: 6.75% decline in Sundarbans Blue Carbon density detected (2017-2026). The truth is in the pixels. #CrowAudit #ClimateTruth"
        response = client.create_tweet(text=text)
        print(f"TWEET_SUCCESS: {response.data['id']}")
        
    except Exception as e:
        print(f"EXECUTION_ERROR: {e}")

if __name__ == "__main__":
    run()
