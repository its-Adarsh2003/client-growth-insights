# !/usr/bin/env bash
set -o errexit

# upgrade packaging tools
pip install --upgrade pip setuptools wheel

# bring back distutils for Python 3.12+
pip install setuptools-scm setuptools-distutils

# now install the rest
pip install -r requirements.txt
