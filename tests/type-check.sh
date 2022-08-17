#!/bin/bash

set -e

PROJECT=$1

#touch ${PROJECT}/__init__.py
MYPY_STATUS=$( mypy -p ${PROJECT} | grep -v "test.*" | tee /dev/tty | wc -l | tr -d '[:space:]' )
if [ $MYPY_STATUS -ne 0 ]; then
    echo "mypy failed"
    exit 1
else
    echo "mypy passed"
    exit 0
fi
