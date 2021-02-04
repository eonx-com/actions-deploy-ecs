#!/usr/bin/env bash

export ECS_CLUSTER_NAME=${1}
export ECS_SERVICE_NAME=${2}
export ECS_TASK_NAME=${3}
export ENVIRONMENT=${4}
export IMAGE_TAG=${5}

# Disable Python buffering so that output appears in GitHub Action during execution (otherwise it sits silent until the very end when it dumps the entire log)
export PYTHONUNBUFFERED=TRUE

cd /opt/deploy
pip install -r ./requirements.txt
python ./deploy.py
