import requests
from requests_oauthlib import OAuth1

ck = "LHguVtqM5rD79ph1UN15WZfYN"
cs = "VHZcBe40gxzhQLbDA05dkCaXmCrG5z7L2uFgpq8qsu0DI3sNEH"
at = "2016338561885470722-4sS8ggwsuULtlQf3GixATSEKUlStkh"
ats = "HeXNnDHsTNmWZMLLLocCacwG0a8J9aYgm74aFw7RY07DJ"

auth = OAuth1(ck, cs, at, ats)
url = "https://api.twitter.com/1.1/account/verify_credentials.json"
r = requests.get(url, auth=auth)
print(f"Status: {r.status_code}")
print(f"Body: {r.text}")
