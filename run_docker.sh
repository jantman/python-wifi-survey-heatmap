#!/bin/bash -x
if [ -z ${1+x} ]; then
  echo "ERROR: Argument (title) needed"
  exit 1
fi
docker run \
  --net="host" \
  --privileged \
  --name survey \
  -it \
  --rm \
  -v $(pwd):/pwd \
  -w /pwd \
  -e DISPLAY=$DISPLAY \
  -v "$HOME/.Xauthority:/root/.Xauthority:ro" \
  jantman/python-wifi-survey-heatmap:23429a4 \
  wifi-survey -vv wlp59s0 192.168.0.24 with_marks.png $1
