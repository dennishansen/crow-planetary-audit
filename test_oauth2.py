import os
import requests
import base64

def test_oauth2():
    client_id = os.environ.get('TWITTER_CLIENT_ID', '').strip("'").strip('"')
    client_secret = os.environ.get('TWITTER_CLIENT_SECRET', '').strip("'").strip('"')
    
    if not client_id or not client_secret:
        print("OAUTH2_MISSING_KEYS")
        return

    # Basic Auth header for token request
    auth_str = f"{client_id}:{client_secret}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    try:
        response = requests.post("https://api.twitter.com/oauth2/token", headers=headers, data=data)
        print(f"OAUTH2_STATUS: {response.status_code}")
        print(f"OAUTH2_RESPONSE: {response.text}")
    except Exception as e:
        print(f"OAUTH2_ERROR: {e}")

if __name__ == "__main__":
    test_oauth2()
