import os
from requests_oauthlib import OAuth1Session

def clean(key):
    val = os.environ.get(key, "")
    return val.strip("'").strip('"')

ck = clean('TWITTER_CONSUMER_KEY')
cs = clean('TWITTER_CONSUMER_SECRET')
at = clean('TWITTER_ACCESS_TOKEN')
ats = clean('TWITTER_ACCESS_TOKEN_SECRET')

url = "https://api.twitter.com/1.1/account/verify_credentials.json"
twitter = OAuth1Session(ck, client_secret=cs, resource_owner_key=at, resource_owner_secret=ats)

try:
    r = twitter.get(url)
    print(f"STATUS_CODE: {r.status_code}")
    print(f"RESPONSE: {r.text}")
except Exception as e:
    print(f"REQUEST_ERROR: {e}")
