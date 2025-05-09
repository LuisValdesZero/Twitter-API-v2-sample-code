import os
import sys
import base64
import hashlib
import re
import time
import requests
from requests_oauthlib import OAuth2Session

MEDIA_ENDPOINT_URL = 'https://api.x.com/2/media/upload'
POST_TO_X_URL = 'https://api.x.com/2/tweets'

# Replace with path to file
VIDEO_FILENAME = 'REPLACE_ME'

# You will need to enable OAuth 2.0 in your App’s auth settings in the Developer Portal to get your client ID.
# Inside your terminal you will need to set an environment variable
# export CLIENT_ID='your-client-id'
client_id = os.environ.get("CLIENT_ID")

# If you have selected a type of App that is a confidential client you will need to set a client secret.
# Confidential Clients securely authenticate with the authorization server.

# Inside your terminal you will need to set an environment variable
# export CLIENT_SECRET='your-client-secret'

# Remove the comment on the following line if you are using a confidential client
# client_secret = os.environ.get("CLIENT_SECRET")

# Replace the following URL with your callback URL, which can be obtained from your App's auth settings.
redirect_uri = "https://www.example.com"

# Set the scopes
scopes = ["media.write", "users.read", "tweet.read", "tweet.write", "offline.access"]

# Create a code verifier
code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

# Create a code challenge
code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
code_challenge = code_challenge.replace("=", "")

# Start and OAuth 2.0 session
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)

# Create an authorize URL
auth_url = "https://x.com/i/oauth2/authorize"
authorization_url, state = oauth.authorization_url(
    auth_url, code_challenge=code_challenge, code_challenge_method="S256"
)

# Visit the URL to authorize your App to make requests on behalf of a user
print(
    "Visit the following URL to authorize your App on behalf of your X handle in a browser:"
)
print(authorization_url)

# Paste in your authorize URL to complete the request
authorization_response = input(
    "Paste in the full URL after you've authorized your App:\n"
)

# Fetch your access token
token_url = "https://api.x.com/2/oauth2/token"

# The following line of code will only work if you are using a type of App that is a public client
auth = False

# If you are using a confidential client you will need to pass in basic encoding of your client ID and client secret.

# Please remove the comment on the following line if you are using a type of App that is a confidential client
# auth = HTTPBasicAuth(client_id, client_secret)

token = oauth.fetch_token(
    token_url=token_url,
    authorization_response=authorization_response,
    auth=auth,
    client_id=client_id,
    include_client_id=True,
    code_verifier=code_verifier,
)

# Your access token
access = token["access_token"]

headers = {
    "Authorization": "Bearer {}".format(access),
    "Content-Type": "application/json",
    "User-Agent": "MediaUploadSampleCode",
}


class VideoPost(object):

    def __init__(self, file_name):
        # Defines video Post properties
        self.video_filename = file_name
        self.total_bytes = os.path.getsize(self.video_filename)
        self.media_id = None
        self.processing_info = None

    def upload_init(self):
        # Initializes Upload
        print('INIT')

        request_data = {
            'command': 'INIT',
            'media_type': 'video/mp4',
            'total_bytes': self.total_bytes,
            'media_category': 'tweet_video'
        }

        req = requests.post(url=MEDIA_ENDPOINT_URL, params=request_data, headers=headers)
        print(req.status_code)
        print(req.text)
        media_id = req.json()['data']['id']

        self.media_id = media_id

        print('Media ID: %s' % str(media_id))

    def upload_append(self):
        segment_id = 0
        bytes_sent = 0
        with open(self.video_filename, 'rb') as file:
            while bytes_sent < self.total_bytes:
                chunk = file.read(4 * 1024 * 1024)  # 4MB chunk size

                print('APPEND')

                files = {'media': ('chunk', chunk, 'application/octet-stream')}

                data = {
                    'command': 'APPEND',
                    'media_id': self.media_id,
                    'segment_index': segment_id
                }

                headers = {
                    "Authorization": f"Bearer {access}",
                    "User-Agent": "MediaUploadSampleCode",
                }

                req = requests.post(url=MEDIA_ENDPOINT_URL, data=data, files=files, headers=headers)

                if req.status_code < 200 or req.status_code > 299:
                    print(req.status_code)
                    print(req.text)
                    sys.exit(0)

                segment_id += 1
                bytes_sent = file.tell()

                print(f'{bytes_sent} of {self.total_bytes} bytes uploaded')

        print('Upload chunks complete.')

    def upload_finalize(self):

        # Finalizes uploads and starts video processing
        print('FINALIZE')

        request_data = {
            'command': 'FINALIZE',
            'media_id': self.media_id
        }

        req = requests.post(url=MEDIA_ENDPOINT_URL, params=request_data, headers=headers)

        print(req.json())

        self.processing_info = req.json()['data'].get('processing_info', None)
        self.check_status()

    def check_status(self):
        # Checks video processing status
        if self.processing_info is None:
            return

        state = self.processing_info['state']

        print('Media processing status is %s ' % state)

        if state == u'succeeded':
            return

        if state == u'failed':
            sys.exit(0)

        check_after_secs = self.processing_info['check_after_secs']

        print('Checking after %s seconds' % str(check_after_secs))
        time.sleep(check_after_secs)

        print('STATUS')

        request_params = {
            'command': 'STATUS',
            'media_id': self.media_id
        }

        req = requests.get(url=MEDIA_ENDPOINT_URL, params=request_params, headers=headers)

        self.processing_info = req.json()['data'].get('processing_info', None)
        self.check_status()

    def post(self):

        # Publishes Post with attached video
        payload = {
            'text': 'I just uploaded a video with the media upload v2 @XDevelopers API.',
            'media': {
                'media_ids': [self.media_id]
            }
        }

        req = requests.post(url=POST_TO_X_URL, json=payload, headers=headers)

        print(req.json())


if __name__ == '__main__':
    videoPost = VideoPost(VIDEO_FILENAME)
    videoPost.upload_init()
    videoPost.upload_append()
    videoPost.upload_finalize()
    videoPost.post()
