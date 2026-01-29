import os
import tweepy

def clean(key):
    val = os.environ.get(key, "")
    return val.strip("'").strip('"')

def test():
    ck = clean('TWITTER_CONSUMER_KEY')
    cs = clean('TWITTER_CONSUMER_SECRET')
    at = clean('TWITTER_ACCESS_TOKEN')
    ats = clean('TWITTER_ACCESS_TOKEN_SECRET')
    
    try:
        client = tweepy.Client(
            consumer_key=ck, consumer_secret=cs,
            access_token=at, access_token_secret=ats
        )
        response = client.get_me()
        if response.data:
            print(f"CLEAN_AUTH_SUCCESS: {response.data.username}")
        else:
            print("CLEAN_AUTH_FAILURE: No data.")
    except Exception as e:
        print(f"CLEAN_AUTH_ERROR: {e}")

if __name__ == "__main__":
    test()
