#!/bin/bash
set -ev
REPO="dddecaf/metabolic-ninja"
GIT_MASTER_HEAD_SHA=$(git rev-parse --short=12 --verify HEAD)
BRANCH=${TRAVIS_BRANCH:=$(git symbolic-ref --short HEAD)}
docker build -f Dockerfile -t $REPO:$BRANCH .
docker tag $REPO:$BRANCH $REPO:$GIT_MASTER_HEAD_SHA
if [ $BRANCH = "master" ] || [ $BRANCH = "devel" ]; then
    docker push $REPO:$BRANCH
    docker push $REPO:$GIT_MASTER_HEAD_SHA
    docker tag $REPO:$BRANCH $REPO:latest
    docker push $REPO:latest
fi