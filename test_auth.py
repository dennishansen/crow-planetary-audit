import os
import tweepy

def test():
    try:
        # Testing v2 authentication
        client = tweepy.Client(
            consumer_key=os.environ.get('TWITTER_CONSUMER_KEY'),
            consumer_secret=os.environ.get('TWITTER_CONSUMER_SECRET'),
            access_token=os.environ.get('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        )
        response = client.get_me()
        if response.data:
            print(f"AUTH_SUCCESS: Authenticated as {response.data.username}")
        else:
            print("AUTH_FAILURE: No data returned.")
    except Exception as e:
        print(f"AUTH_ERROR: {e}")

if __name__ == "__main__":
    test()
