import tweepy
from dotenv import load_dotenv
import os


def create_api():
    # load values stored in a file called ".env"
    load_dotenv()
    bearer_token = os.getenv("BEARER_TOKEN")

    # use Tweepy API v1.1
    auth = tweepy.OAuth2BearerHandler(bearer_token)
    api = tweepy.API(auth, wait_on_rate_limit=True)

    print("API set up")
    return api
