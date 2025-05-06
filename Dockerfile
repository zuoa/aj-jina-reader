FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN \
    set -eux; \
    pip3 install --no-cache-dir -r requirements.txt

COPY app ./app
WORKDIR /app/app
ENV TZ=Asia/Shanghai
ENV PYTHONPATH="/app:$PYTHONPATH"
EXPOSE 6090/tcp
VOLUME /data
ENTRYPOINT ["python", "app.py"]