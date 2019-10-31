# Python support can be specified down to the minor or micro version
# (e.g. 3.6 or 3.6.3).
# OS Support also exists for jessie & stretch (slim and full).
# See https://hub.docker.com/r/library/python/ for all supported Python
# tags from Docker Hub.
FROM python:3.7-alpine

LABEL Name=dvb

WORKDIR /app
ADD . /app

RUN apk add  --no-cache ffmpeg

RUN pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

CMD ["python3", "dvb.py"]