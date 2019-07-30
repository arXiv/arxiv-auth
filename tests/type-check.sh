#!/bin/bash

set -e

PROJECT=$1

touch ${PROJECT}/__init__.py
MYPY_STATUS=$( pipenv run mypy -p ${PROJECT} | grep -v "test.*" | tee /dev/tty | wc -l | tr -d '[:space:]' )
if [ $MYPY_STATUS -ne 0 ]; then MYPY_STATE="failure" && echo "mypy failed"; else MYPY_STATE="success" &&  echo "mypy passed"; fi
if [ "$TRAVIS_PULL_REQUEST_SHA" = "" ];  then SHA=$TRAVIS_COMMIT; else SHA=$TRAVIS_PULL_REQUEST_SHA; fi
if [ -z ${GITHUB_TOKEN} ]; then
    echo "Github token not set; will not report results";
else
    curl -u $USERNAME:$GITHUB_TOKEN \
        -d '{"state": "'$MYPY_STATE'", "target_url": "https://travis-ci.org/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "description": "", "context": "code-quality/mypy"}' \
        -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA \
        > /dev/null 2>&1;
    echo "Sent mypy results to Github"
fi