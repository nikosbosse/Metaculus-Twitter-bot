import datetime
import requests
import yaml

import pandas as pd

CONFIG_FILE = "config.yml"


class predictions:
    def __init__(self):
        with open(CONFIG_FILE) as file:
            self.config = yaml.load(file, Loader=yaml.FullLoader)
        self.question_ids = self.config["questions"]
        self.filters = self.config["filters"]
        self.thresholds = self.config["thresholds"]
        self.tweets = []

    def create_threshold(self, hours):
        return datetime.datetime.now() - datetime.timedelta(hours=hours)

    def add_tweet(
        self, last_prediction, current_prediction, change, elapsed, title, url
    ):
        has_increased = change > 0
        arrow = "🔼" if has_increased else "🔽"
        added_sign = "+" if has_increased else ""

        current_pred_formatted = str(round(current_prediction * 100)) + "%"
        last_pred_formatted = str(round(last_prediction * 100)) + "%"
        change_formatted = f"{added_sign}{round(change * 100)}%"

        tweet = f"{arrow} {title}"
        tweet += f"\nCommunity prediction: {current_pred_formatted}"
        tweet += f"\n{change_formatted} in the last {elapsed} hours"
        tweet += f"\nfrom {last_pred_formatted} to {current_pred_formatted}"
        tweet += f"\nhttps://www.metaculus.com{url}"

        print("Tweet added!")
        self.tweets.append(tweet)

    def get(self):

        # for every question, get past community predictions and compare whether there has been a significant change
        for id in self.question_ids:

            # read JSON file from public Metaculus API
            question_url = "https://www.metaculus.com/api2/questions/" + str(id)
            data = requests.get(question_url).json()

            title = data["title"]
            print(f"{id} - {title}")
            timeseries = data["community_prediction"]["history"]

            df = pd.DataFrame.from_records(timeseries, columns=["t", "x1"])
            df["prediction"] = df.x1.apply(pd.Series)["q2"]
            df = df.drop(columns=["x1"]).rename(columns={"t": "time"})

            # convert timestamps to datetime
            df["time"] = pd.to_datetime(df.time, unit="s")

            # check filters: does the question qualify?
            minimum_time = self.create_threshold(hours=self.filters["minimum_hours"])
            if (
                df.time.min() > minimum_time
                or data["number_of_predictions"] < self.filters["minimum_forecasts"]
            ):
                print("Question skipped")
                next

            # save latest time and prediction
            current_prediction = df.prediction.values[-1]

            # identify large swings
            for threshold in self.thresholds:
                time_limit = self.create_threshold(hours=threshold["hours"])
                last_prediction = df[df.time < time_limit].prediction.values[-1]
                change = current_prediction - last_prediction

                if abs(change) > threshold["swing"]:
                    self.add_tweet(
                        last_prediction=last_prediction,
                        current_prediction=current_prediction,
                        change=change,
                        elapsed=threshold["hours"],
                        title=title,
                        url=data["page_url"],
                    )
                    break

        return self.tweets
