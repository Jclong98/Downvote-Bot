FROM python:3.8

LABEL Name=dvb

WORKDIR /app
ADD . /app

# RUN apk add  --no-cache ffmpeg gcc libsodium-dev
RUN apt-get update
RUN apt-get install -y \
    ffmpeg \
    gcc \
    libsodium-dev 

RUN pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

CMD ["python3", "dvb.py"]