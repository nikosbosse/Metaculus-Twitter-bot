import datetime
import re
import time
import yaml

import pandas as pd

from create_api import create_api
from get_predictions import predictions


def get_config():
    with open("config.yml") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config


def get_recent_alerts(no_duplicate_period):
    alerts = pd.read_csv("alerts.csv")
    threshold = datetime.datetime.utcnow() - datetime.timedelta(
        hours=no_duplicate_period
    )
    recently_tweeted = alerts[pd.to_datetime(alerts.last_alert_timestamp) >= threshold]
    return recently_tweeted.question_id.values


def write_recent_alerts(tweets):
    old_alerts = pd.read_csv("alerts.csv")
    new_alerts = pd.DataFrame(
        {
            "question_id": [t["question_id"] for t in tweets],
            "last_alert_timestamp": [str(datetime.datetime.utcnow())],
        }
    )
    alerts = (
        pd.concat([old_alerts, new_alerts]).groupby("question_id", as_index=False).max()
    )
    alerts.to_csv("alerts.csv", index=False)
    return True


def post_tweet(event="", context=""):
    config = get_config()

    api = create_api()
    print("API created")

    recent_alerts = get_recent_alerts(config["filters"]["no_duplicate_period"])
    print(f"Fetched recent alerts: {recent_alerts}")

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
    write_recent_alerts(tweets)


if __name__ == "__main__":
    post_tweet()
