#!/bin/bash
PIPENV_VERBOSITY=-1 pipenv run pydocstyle --convention=numpy --add-ignore=D401 "$@"
