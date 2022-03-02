from create_api import create_api
from get_predictions import prediction
import time

def post_tweet(event="", context=""):
    api = create_api()
    print("API created")
    p = prediction()
    for tweet in p.tweets: 
        try:
            if tweet: 
                api.create_tweet(text=tweet)
                print(tweet)
                time.sleep(30)
        except Exception as e:
            raise e