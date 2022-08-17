#!/bin/bash

PROJECT="$@"

if [ -z ${MIN_SCORE} ]; then MIN_SCORE="8"; fi

PYLINT_SCORE=$( PIPENV_VERBOSITY=-1 pylint ${PROJECT} | tail -2 | grep -Eo '[0-9\.]+/10' | tail -1 | sed s/\\/10// )

if (( $(echo "$PYLINT_SCORE > $MIN_SCORE"|bc -l) )); then
    echo "pylint passed with score "$PYLINT_SCORE
    exit 0
else
    echo "pylint failed with score: $PYLINT_SCORE min: score $MIN_SCORE"
    exit 1
fi

