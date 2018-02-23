#!/bin/sh

# The status endpoint will differ based on whether this is a PR or commit.
# if [ "$TRAVIS_PULL_REQUEST_SHA" = "" ];  then SHA=$TRAVIS_COMMIT; else SHA=$TRAVIS_PULL_REQUEST_SHA; fi
#
# # Check that accounts builds
# echo "Build arxiv/accounts in $TRAVIS_BUILD_DIR";
# docker build $TRAVIS_BUILD_DIR -t arxiv/accounts -f $TRAVIS_BUILD_DIR/Dockerfile
# DOCKER_BUILD_ZERO_STATUS=$?
# if [ $DOCKER_BUILD_ZERO_STATUS -ne 0 ]; then
#     DOCKER_BUILD_ZERO_STATE="failure" && echo "docker build accounts failed";
# else DOCKER_BUILD_ZERO_STATE="success" &&  echo "docker build accounts passed";
# fi
#
# curl -u $USERNAME:$GITHUB_TOKEN \
#     -d '{"state": "'$DOCKER_BUILD_ZERO_STATE'", "target_url": "https://travis-ci.org/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "description": "", "context": "docker/build"}' \
#     -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA \
#     > /dev/null 2>&1
#
# # Check that accounts runs
# docker run -d -p 8000:8000 --name arxiv-accounts-test arxiv/accounts
# DOCKER_RUN_ZERO_STATUS=$?
# if [ $DOCKER_RUN_ZERO_STATUS -ne 0 ]; then
#     DOCKER_RUN_ZERO_STATE="failure" && echo "docker run accounts failed";
# else DOCKER_RUN_ZERO_STATE="success" &&  echo "docker run accounts passed";
# fi
#
# curl -u $USERNAME:$GITHUB_TOKEN \
#     -d '{"state": "'$DOCKER_RUN_ZERO_STATE'", "target_url": "https://travis-ci.org/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "description": "", "context": "docker/run"}' \
#     -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA \
#     > /dev/null 2>&1
#
# sleep 5s
#
# # Check service is running as expected
# curl http://localhost:8000/accounts/api/status | grep "nobody but us"
# CURL_TEST_ZERO_STATUS=$?
# if [ $CURL_TEST_ZERO_STATUS -ne 0 ]; then
#     CURL_TEST_ZERO_STATE="failure" && echo "curl failed";
# else CURL_TEST_ZERO_STATE="success" &&  echo "curl passed";
# fi
#
# curl -u $USERNAME:$GITHUB_TOKEN \
#     -d '{"state": "'$CURL_TEST_ZERO_STATE'", "target_url": "https://travis-ci.org/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "description": "", "context": "curl/basic"}' \
#     -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA \
#     > /dev/null 2>&1
