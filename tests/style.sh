#!/bin/bash
PIPENV_VERBOSITY=-1 pydocstyle --convention=numpy --add-ignore=D401 "$@"
