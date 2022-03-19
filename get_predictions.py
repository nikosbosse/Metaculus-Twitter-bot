from calendar import c
import datetime
import re
import requests
import tempfile

from matplotlib.dates import DateFormatter
from matplotlib.pyplot import style
import matplotlib.ticker as mtick
import pandas as pd

CONFIG_FILE = "config.yml"


class predictions:
    def __init__(self, config, recent_alerts):
        self.projects = config["projects"]
        self.questions = config["questions"]
        self.filters = config["filters"]
        self.thresholds = config["thresholds"]
        self.recent_alerts = recent_alerts
        self.tweets = []

    def get_question_ids(self):
        ids = set(self.questions)
        for project in self.projects:
            question_list = requests.get(
                f"https://www.metaculus.com/api2/questions/?project={project}&status=open&type=forecast&limit=999"
            ).json()["results"]
            ids = ids.union([q["id"] for q in question_list])
        return sorted(list(ids))

    def create_threshold(self, hours):
        return datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

    def is_question_included(self, title, data):
        if title in self.recent_alerts:
            print("Question skipped (recent alert)")
            return False
        if data["number_of_predictions"] < self.filters["minimum_forecasts"]:
            print("Question skipped (too few forecasts)")
            return False
        if data["possibilities"]["type"] not in self.filters["types"]:
            print(
                f"Question skipped (type {data['possibilities']['type']} not handled)"
            )
            return False
        if len(data["community_prediction"]["history"]) == 0:
            print("Question skipped (timeseries is empty)")
            return False
        return True

    def make_chart(self, df, title_short):
        if df.time.min() < self.create_threshold(24 * 365.2425):
            date_format = "%B %Y"
        elif df.time.min() > self.create_threshold(24 * 5):
            date_format = "%-d %b %H:%M"
        else:
            date_format = "%-d %b"

        style.use("dark_background")  # Sets all text and lines to white
        ax = df.plot(
            x="time",
            y=["lower", "prediction", "upper"],
            kind="line",
            color=(
                [110 / 255, 116 / 255, 127 / 255, 0.8],  # "#61676D",
                "#AEB1B4",
                [110 / 255, 116 / 255, 127 / 255, 0.8],  # "#61676D", # "#61676D"
            ),
            linewidth=2,
            ylim=(0, 1),
            xlabel="",
            ylabel="Metaculus community prediction",
            legend=False,
            fontsize=14,
            figsize=(14, 8),
        )
        ax.set_title(title_short, fontsize=18)
        ax.set_facecolor("#282F37")
        ax.fill_between(df["time"], df["lower"], df["upper"], color="w", alpha=0.1)

        ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
        ax.xaxis.set_major_formatter(DateFormatter(date_format))

        ax.grid("on", axis="y", linewidth=0.2)
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.margins(x=0)

        with tempfile.NamedTemporaryFile(mode="wb", dir="/tmp") as png:
            filepath = f"{png.name}.png"
            ax.get_figure().savefig(
                filepath,
                bbox_inches="tight",
                pad_inches=0.2,
                dpi=300,
                facecolor="#282F37",  #'none' maybe?
                transparent=False,
            )
        return filepath

    def add_tweet(
        self,
        alert_type,
        df,
        current_prediction,
        change,
        elapsed,
        title,
        title_short,
        url,
    ):

        if alert_type == "Swing":
            has_increased = change > 0
            arrow = "⬆️" if has_increased else "⬇️"
            added_sign = "+" if has_increased else ""

            change_formatted = f"{added_sign}{round(change * 100)}%"

            alert_text = f"\n{arrow} {change_formatted} in the last {elapsed} hours\n"

        if alert_type == "New":
            alert_text = f"\n🆕 New question\n"

        current_pred_formatted = str(round(current_prediction * 100)) + "%"

        tweet = f"{title}"
        tweet += f"\n\nCommunity prediction: {current_pred_formatted}"
        tweet += alert_text
        tweet += f"https://www.metaculus.com{url}"

        chart_path = self.make_chart(df, title_short)
        self.tweets.append({"text": tweet, "chart": chart_path})
        print("Tweet added!")

    def get(self):

        question_ids = self.get_question_ids()

        # for every question, get past community predictions and compare whether there has been a significant change
        for id in question_ids:
            question_url = "https://www.metaculus.com/api2/questions/" + str(id)
            data = requests.get(question_url).json()

            # clean Metaculus' titles
            title = re.sub("\s+", " ", data["title"])
            title_short = re.sub("\s+", " ", data["title_short"])

            print(f"{id} - {title}")

            if self.is_question_included(title, data):
                timeseries = data["community_prediction"]["history"]
                df = pd.DataFrame.from_records(timeseries, columns=["t", "x1"])
                try:
                    df[["lower", "prediction", "upper"]] = df.x1.apply(pd.Series)
                except Exception:
                    print(f"ERROR: Unknown error with question: {id} - {title}")
                    continue
                df = df.drop(columns=["x1"]).rename(columns={"t": "time"})

                # convert timestamps to datetime
                df["time"] = pd.to_datetime(df.time, unit="s")

                # save current prediction
                current_prediction = df.prediction.values[-1]

                # check if question is new and add tweet if so
                if pd.to_datetime(
                    data["publish_time"].replace("Z", "")
                ) > self.create_threshold(hours=self.filters["minimum_hours"]):

                    self.add_tweet(
                        alert_type="New",
                        df=df,
                        current_prediction=current_prediction,
                        change=change,
                        elapsed=threshold["hours"],
                        title=title,
                        title_short=title_short,
                        url=data["page_url"],
                    )

                else:
                    # identify large swings
                    for threshold in self.thresholds:
                        time_limit = self.create_threshold(hours=threshold["hours"])
                        last_prediction = df[df.time < time_limit].prediction.values[-1]
                        change = current_prediction - last_prediction

                        if abs(change) > threshold["swing"]:
                            self.add_tweet(
                                alert_type="Swing",
                                df=df,
                                current_prediction=current_prediction,
                                change=change,
                                elapsed=threshold["hours"],
                                title=title,
                                title_short=title_short,
                                url=data["page_url"],
                            )
                            break

        return self.tweets
