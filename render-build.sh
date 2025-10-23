# !/usr/bin/env bash
set -o errexit

# upgrade tools
pip install --upgrade pip setuptools wheel

# manually bring back distutils
pip install setuptools-scm
pip install setuptools==68.0.0

# now install the rest
pip install -r requirements.txt
