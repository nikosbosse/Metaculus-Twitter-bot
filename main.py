import time

from create_api import create_api
from get_predictions import predictions

def post_tweet(event="", context=""):
    api = create_api()
    print("API created")
    p = predictions()
    tweets = p.get()

    print("---")
    print(f"{len(tweets)} tweets queued…")
    for tweet in tweets:
        try:
            if tweet:
                api.create_tweet(text=tweet)
                print("")
                print(tweet)
                time.sleep(10)
        except Exception as e:
            raise e


if __name__ == "__main__":
    post_tweet()
