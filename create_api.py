import tweepy
from dotenv import load_dotenv
import os


def create_api():
    # load values stored in a file called ".env"
    load_dotenv()
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("BEARER_TOKEN")

    # use Tweepy API v1.1
    #auth = tweepy.OAuth2BearerHandler(bearer_token)
    #api = tweepy.Client(auth, wait_on_rate_limit=True)

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(
        auth, wait_on_rate_limit=True)

    print("API set up")
    return api
