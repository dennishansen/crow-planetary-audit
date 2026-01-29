import os
import tweepy

def clean_val(key):
    val = os.environ.get(key, "")
    # Remove literal single quotes, double quotes, and whitespace
    cleaned = val.replace("'", "").replace('"', "").strip()
    return cleaned

def check():
    ck = clean_val('TWITTER_CONSUMER_KEY')
    cs = clean_val('TWITTER_CONSUMER_SECRET')
    at = clean_val('TWITTER_ACCESS_TOKEN')
    ats = clean_val('TWITTER_ACCESS_TOKEN_SECRET')
    
    print(f"Testing with cleaned keys (Lengths: CK={len(ck)}, CS={len(cs)}, AT={len(at)}, ATS={len(ats)})")
    
    try:
        # Test v2
        client = tweepy.Client(
            consumer_key=ck, consumer_secret=cs,
            access_token=at, access_token_secret=ats
        )
        me = client.get_me()
        if me.data:
            print(f"SUCCESS: Authenticated as {me.data.username}")
            return True
    except Exception as e:
        print(f"V2_FAILED: {e}")
        
    try:
        # Test v1.1
        auth = tweepy.OAuth1UserHandler(ck, cs, at, ats)
        api = tweepy.API(auth)
        user = api.verify_credentials()
        if user:
            print(f"SUCCESS: Authenticated as {user.screen_name}")
            return True
    except Exception as e:
        print(f"V1_FAILED: {e}")
    
    return False

if __name__ == "__main__":
    check()
