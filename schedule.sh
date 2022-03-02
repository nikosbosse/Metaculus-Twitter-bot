#!bin/bash
# use create instead of update to create it for the first time
gcloud scheduler jobs update pubsub metaculus-alert \
    --project=metaculus-alert \
    --schedule="0 */6 * * *" \
    --location=us-central1 \
    --topic=metaculus-alert \
    --description="Check Metaculus predictions update" \
    --message-body="Check Metaculus predictions update" \
    --time-zone=GMT