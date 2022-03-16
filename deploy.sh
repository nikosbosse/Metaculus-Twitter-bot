#!bin/bash

gcloud functions delete metaculus-alert \
    --project=metaculus-alert 

gcloud functions deploy metaculus-alert \
    --project=metaculus-alert \
    --trigger-topic metaculus-alert \
    --memory=1024MB \
    --env-vars-file .env.yaml \
    --region=us-central1 \
    --runtime python39 \
    --entry-point=post_tweet \
    --timeout=300