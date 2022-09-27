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

    def hours_ago(self, hours):
        return datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

    def is_question_included(self, data, prediction_type, prediction_format):
        if data["id"] in self.recent_alerts:
            print("Question skipped (recent alert)")
            return False
        if data["number_of_predictions"] < self.filters["minimum_forecasts"]:
            print("Question skipped (too few forecasts)")
            return False
        if prediction_type not in self.filters["types"]:
            print(
                f"Question skipped (type {data['possibilities']['type']} not handled)"
            )
            return False
        if prediction_format == "date":
            print(f"Question skipped (date format not handled)")
            return False
        if len(data["community_prediction"]["history"]) == 0:
            print("Question skipped (timeseries is empty)")
            return False
        return True

    def make_chart(self, df, title_short, prediction_type):
        if df.time.min() < self.hours_ago(24 * 365.2425):
            date_format = "%B %Y"
        elif df.time.min() > self.hours_ago(24 * 5):
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
            xlabel="",
            ylabel="Metaculus community prediction",
            legend=False,
            fontsize=14,
            figsize=(14, 8),
        )

        if prediction_type == "binary":
            ax.set_ylim([0, 1])
            ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))

        ax.set_title(title_short, fontsize=18)
        ax.set_facecolor("#282F37")
        ax.fill_between(df["time"], df["lower"], df["upper"], color="w", alpha=0.1)

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
        prediction_type,
        alert_type,
        df,
        current_prediction,
        change,
        elapsed,
        title,
        title_short,
        url,
        question_id,
    ):

        if alert_type == "swing":
            has_increased = change > 0
            arrow = "⬆️" if has_increased else "⬇️"
            added_sign = "+" if has_increased else ""

            if prediction_type == "binary":
                change_formatted = f"{added_sign}{round(change * 100)}%"
                alert_text = (
                    f"\n{arrow} {change_formatted} in the last {elapsed} hours\n"
                )
                current_pred_formatted = str(round(current_prediction * 100)) + "%"

            if prediction_type == "continuous":
                if current_prediction <= 100:
                    change_formatted = f"{added_sign}{round(change, 2)}"
                    current_pred_formatted = str(round(current_prediction, 2))
                elif current_prediction >= 1e6:
                    change_formatted = f"{added_sign}{int(change / 1e6)} million"
                    current_pred_formatted = (
                        f"{round(current_prediction / 1e6), 1} million"
                    )
                else:
                    change_formatted = f"{added_sign}{int(change)}"
                    current_pred_formatted = str(int(current_prediction))
                alert_text = (
                    f"\n{arrow} {change_formatted} in the last {elapsed} hours\n"
                )

        elif alert_type == "new":
            alert_text = f"\n🆕 New question\n"

        tweet = f"{title}"
        tweet += f"\n\nCommunity prediction: {current_pred_formatted}"
        tweet += alert_text
        tweet += f"https://www.metaculus.com{url}"

        chart_path = self.make_chart(df, title_short, prediction_type=prediction_type)
        self.tweets.append(
            {"text": tweet, "chart": chart_path, "question_id": question_id}
        )
        print("Tweet added!")

    # recover actual predicted values from the transformed values between 0 and 1
    def recover_values(self, prediction, lower_bound, upper_bound, deriv_ratio):
        if deriv_ratio == 1:
            value = lower_bound + (upper_bound - lower_bound) * prediction
        else:
            value = lower_bound + (upper_bound - lower_bound) * (
                deriv_ratio**prediction - 1
            ) / (deriv_ratio - 1)
        return value

    def get(self):

        question_ids = self.get_question_ids()

        # for every question, get past community predictions and compare whether there has been a significant change
        for id in question_ids:
            question_url = "https://www.metaculus.com/api2/questions/" + str(id)
            data = requests.get(question_url).json()

            # clean Metaculus' titles
            title = re.sub("\s+", " ", data["title"])
            title_short = re.sub("\s+", " ", data["title_short"])
            try:
                prediction_type = data["possibilities"]["type"]
            except:
                next
            prediction_format = data["possibilities"].get("format")

            print(f"{id} - {title}")
            if self.is_question_included(data, prediction_type, prediction_format):

                timeseries = data["community_prediction"]["history"]
                df = pd.DataFrame.from_records(timeseries, columns=["t", "x1"])

                # convert to timeseries, works for binary as well as continuous
                try:
                    df[["lower", "prediction", "upper"]] = df.x1.apply(pd.Series).iloc[
                        :, 0:3
                    ]
                except Exception:
                    print(f"ERROR: Unknown error with question: {id} - {title}")
                    continue
                df = df.drop(columns=["x1"]).rename(columns={"t": "time"})

                # convert timestamps to datetime
                df["time"] = pd.to_datetime(df.time, unit="s")

                if prediction_type == "continuous":
                    lower_bound = data["possibilities"]["scale"]["min"]
                    upper_bound = data["possibilities"]["scale"]["max"]
                    deriv_ratio = data["possibilities"]["scale"]["deriv_ratio"]

                    df[["lower", "prediction", "upper"]] = df[
                        ["lower", "prediction", "upper"]
                    ].apply(
                        lambda x: self.recover_values(
                            x,
                            lower_bound=lower_bound,
                            upper_bound=upper_bound,
                            deriv_ratio=deriv_ratio,
                        ),
                        axis=1,
                    )

                # save current prediction
                current_prediction = df.prediction.values[-1]

                # check if question is new and add tweet if so
                if pd.to_datetime(
                    data["publish_time"].replace("Z", "")
                ) > self.hours_ago(hours=self.filters["no_duplicate_period"]):

                    self.add_tweet(
                        alert_type="new",
                        df=df,
                        current_prediction=current_prediction,
                        prediction_type=prediction_type,
                        change=None,
                        elapsed=threshold["hours"],
                        title=title,
                        title_short=title_short,
                        url=data["page_url"],
                        question_id=data["id"],
                    )

                elif pd.to_datetime(
                    data["publish_time"].replace("Z", "")
                ) < self.hours_ago(hours=self.filters["minimum_hours"]):
                    # identify large swings
                    for threshold in self.thresholds:
                        time_limit = self.hours_ago(hours=threshold["hours"])

                        if len(df[df.time < time_limit]) == 0:
                            print(
                                f"Couldn't do comparison for {title} - no prior forecast available"
                            )
                            continue

                        last_prediction = df[df.time < time_limit].prediction.values[-1]
                        last_prediction_25 = df[df.time < time_limit].lower.values[-1]
                        last_prediction_75 = df[df.time < time_limit].upper.values[-1]

                        if prediction_type == "binary":
                            change = current_prediction - last_prediction
                            if not abs(change) > threshold["swing"]:
                                continue

                        elif prediction_type == "continuous":
                            if not current_prediction > (
                                last_prediction
                                + threshold["swing_continuous"]
                                * (last_prediction_75 - last_prediction)
                            ) or current_prediction < (
                                last_prediction
                                + threshold["swing_continuous"]
                                * (last_prediction_25 - last_prediction)
                            ):
                                continue

                            change = current_prediction - last_prediction

                        # add tweet if loop executed until here
                        self.add_tweet(
                            alert_type="swing",
                            df=df,
                            current_prediction=current_prediction,
                            change=change,
                            prediction_type=prediction_type,
                            elapsed=threshold["hours"],
                            title=title,
                            title_short=title_short,
                            url=data["page_url"],
                            question_id=data["id"],
                        )
                        break

        return self.tweets
