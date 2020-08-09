#!/bin/bash -ex

cd "$( dirname "${BASH_SOURCE[0]}" )"
BDATE=$(date +%Y-%m-%dT%H:%M:%S.00%Z)
REF=$(git rev-parse --short HEAD)
if ! git diff --no-ext-diff --quiet --exit-code || ! git diff-index --cached --quiet HEAD --; then
  REF="${REF}-dirty"
fi

docker build \
  --build-arg "build_date=${BDATE}" \
  --build-arg "repo_url=$(git config remote.origin.url)" \
  --build-arg "repo_ref=${REF}" \
  -t jantman/python-wifi-survey-heatmap:${REF} \
  .
