import tweepy
from dotenv import load_dotenv
import os

def create_api():
    # load values stored in a file called ".env"
    load_dotenv()
    bearer_token = os.getenv("BEARER_TOKEN")
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

    # use Tweepy API v2 Client
    api = tweepy.Client(consumer_key=consumer_key, consumer_secret=consumer_secret,
                        bearer_token = bearer_token,
                        access_token=access_token,
                        access_token_secret=access_token_secret, wait_on_rate_limit=True)
    
    print("API set up")
    return api
    