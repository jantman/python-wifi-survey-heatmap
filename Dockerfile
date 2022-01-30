FROM debian:buster-20200720

ARG build_date
ARG repo_url
ARG repo_ref
USER root

RUN apt-get update && \
  DEBIAN_FRONTEND=noninteractive \
  apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    iperf3 \
    libjpeg-dev \
    pulseaudio-utils \
    python3 \
    python3-cffi \
    python3-dev \
    python3-pip \
    python3-scipy \
    python3-setuptools \
    python3-wheel \
    python3-wxgtk4.0 \
    wireless-tools \
    zlib1g zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

RUN pip3 install iperf3 matplotlib scipy wheel libnl3

COPY . /app

RUN cd /app && \
  python3 setup.py develop && \
  pip3 freeze > /app/requirements.installed

LABEL maintainer="jason@jasonantman.com" \
      org.label-schema.build-date="$build_date" \
      org.label-schema.name="jantman/python-wifi-survey-heatmap" \
      org.label-schema.url="https://github.com/jantman/python-wifi-survey-heatmap" \
      org.label-schema.vcs-url="$repo_url" \
      org.label-schema.vcs-ref="$repo_ref" \
      org.label-schema.version="$repo_ref" \
      org.label-schema.schema-version="1.0"

# For the iperf server, if using for the server side
EXPOSE 5201/tcp
EXPOSE 5201/udp

CMD /bin/bash
