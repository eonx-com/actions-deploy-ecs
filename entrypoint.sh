#!/usr/bin/env bash

export ENVIRONMENT=${1}
export IMAGE_TAG=${2}

cd /opt/deploy
pip install -r ./requirements.txt
python ./deploy.py