#!/usr/bin/env bash

# If a base image is required login to the Docker repository and pull the image first
if [[ ! -z "${DOCKER_BASE_IMAGE_REPOSITORY}" && ! -z "${DOCKER_BASE_IMAGE_REPOSITORY_USERNAME}" && ! -z "${DOCKER_BASE_IMAGE_REPOSITORY_PASSWORD}" && ! -z "${DOCKER_BASE_IMAGE}" ]]; then
  echo "Authenticating: ${DOCKER_BASE_IMAGE_REPOSITORY}..."
  docker login "${DOCKER_BASE_IMAGE_REPOSITORY}" \
    --username "${DOCKER_BASE_IMAGE_REPOSITORY_USERNAME}" \
    --password "${DOCKER_BASE_IMAGE_REPOSITORY_PASSWORD}";
  echo "Pulling: ${DOCKER_BASE_IMAGE_REPOSITORY}/${DOCKER_BASE_IMAGE}..."
  docker pull "${DOCKER_BASE_IMAGE_REPOSITORY}/${DOCKER_BASE_IMAGE}"
fi

export ENVIRONMENT=${1}
export IMAGE_TAG=${2}

# Disable Python buffering so that output appears in GitHub Action during execution (otherwise it sits silent until the very end when it dumps the entire log)
export PYTHONUNBUFFERED=TRUE

cd /opt/deploy
pip install -r ./requirements.txt
python ./deploy.py
