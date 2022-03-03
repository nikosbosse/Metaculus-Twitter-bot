import urllib.request, json
import datetime


class prediction:
    def __init__(self):
        # list of questions for the Ukraine Conflict Challenge. Ideally, this should not be hard-coded, but obtained from the API
        self.ids = [
            9939,
            10002,
            9941,
            9999,
            9930,
            9935,
            9994,
            10004,
            9943,
            9942,
            9993,
            10005,
            9936,
            9937,
            10001,
            9933,
            9991,
            10003,
            9990,
            9988,
            9986,
            9985,
        ]

        self.tweets = []

        # for every question, get past community predictions and compare whether there has been a significant change
        for id in self.ids:
            question_url = "https://www.metaculus.com/api2/questions/" + str(id)

            # read json file from public Metaculus API
            with urllib.request.urlopen(question_url) as url:
                data = json.loads(url.read().decode())

            title = data["title"]
            web_url = data["page_url"]
            timeseries = data["community_prediction"]["history"]
            # only keep relevant entries
            timeseries = [
                {
                    "prediction": timeseries[index]["x1"]["q2"],
                    "time": datetime.datetime.fromtimestamp(timeseries[index]["t"]),
                }
                for index in range(len(timeseries))
            ]

            # save latest time and predictions
            current_time = timeseries[-1]["time"]
            current_prediction = timeseries[-1]["prediction"]

            # filter most recent values - this could be refactored into a function
            time_5 = current_time - datetime.timedelta(hours=5, minutes=0, seconds=0)
            relevant_times_5 = list(
                filter(lambda entry: entry["time"] >= time_5, timeseries)
            )
            diff_5 = relevant_times_5[0]["prediction"] - current_prediction

            relevant_times_24 = list(
                filter(lambda entry: entry["time"] >= time_24, timeseries)
            )
            time_24 = current_time - datetime.timedelta(hours=24, minutes=0, seconds=0)
            diff_24 = relevant_times_24[0]["prediction"] - current_prediction

            if abs(diff_5) > 0.05:
                if diff_5 < 0:
                    direction = "upwards"
                else:
                    direction = "downwards"
                self.tweets.append(
                    "The community prediction for the question\n"
                    + "'"
                    + title
                    + "'\n"
                    + "on Metaculus has changed "
                    + direction
                    + " by more than 5% over the last 5h. \nIt is now at "
                    + str(int(current_prediction * 100))
                    + "% probability.\n\n"
                    + "https://www.metaculus.com/questions/"
                    + str(id)
                    + "/"
                )
            elif abs(diff_24) > 0.1:
                if diff_24 < 0:
                    direction = "upwards"
                else:
                    direction = "downwards"
                self.tweets.append(
                    "The Metaculus community prediction on\n"
                    + "'"
                    + title
                    + "'\n"
                    + "has changed "
                    + direction
                    + " by >10% over the last 24h. \nIt's now at "
                    + str(int(current_prediction * 100))
                    + "%.\n\n"
                    + "https://www.metaculus.com/questions/"
                    + str(id)
                    + "/"
                )
