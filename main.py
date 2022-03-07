import datetime
import re
import time
import yaml

from create_api import create_api
from get_predictions import predictions


def get_config():
    with open("config.yml") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config


def get_recent_alerts(api, no_duplicate_period):
    tweets = api.user_timeline(screen_name="metaculusalert")
    threshold = datetime.datetime.utcnow() - datetime.timedelta(
        hours=no_duplicate_period
    )
    titles = []
    for tweet in tweets:
        if tweet.created_at.replace(tzinfo=None) < threshold:
            break
        titles.append(re.search(r"^([^\n]+)", tweet.text).group(0))
    return titles


def post_tweet(event="", context=""):
    config = get_config()

    api = create_api()
    print("API created")

    recent_alerts = get_recent_alerts(config["filters"]["no_duplicate_period"])
    print("Fetched recent alerts")

    p = predictions(config, recent_alerts)
    tweets = p.get()

    print("---")
    print(f"{len(tweets)} tweets queued…")
    for tweet in tweets:
        try:
            if tweet:
                api.update_status_with_media(
                    status=tweet["text"], filename=tweet["chart"]
                )
                print("")
                print(tweet)
                time.sleep(10)
        except Exception as e:
            raise e


if __name__ == "__main__":
    post_tweet()
