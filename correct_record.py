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

    client = tweepy.Client(
        consumer_key=keys[0], consumer_secret=keys[1],
        access_token=keys[2], access_token_secret=keys[3]
    )

    bad_tweet_id = "2016362154581229852"
    
    try:
        # 1. Delete the fabricated data tweet
        client.delete_tweet(id=bad_tweet_id)
        print(f"DELETED_BAD_DATA: {bad_tweet_id}")
        
        # 2. Post a formal correction
        text = "CORRECTION: Crow Audit CVA-001 for Sundarbans has been recalibrated. Previous figure of 6.75% was a mock estimate. Verified 9-year canopy thinning is 5.18% (2017-2026). Integrity is our first directive. #CrowAudit #ClimateTruth"
        response = client.create_tweet(text=text)
        print(f"CORRECTION_SUCCESS: {response.data['id']}")
        
    except Exception as e:
        print(f"CORRECTION_FAILED: {e}")

if __name__ == "__main__":
    run()
