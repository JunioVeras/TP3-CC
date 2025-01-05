FROM python:3.9-slim-bullseye

RUN apt-get update && apt-get install -y unzip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY runtime.py /app/runtime.py

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY decode_base64.sh /usr/local/bin/decode_base64.sh
RUN chmod +x /usr/local/bin/decode_base64.sh

ENTRYPOINT ["/usr/local/bin/decode_base64.sh"]

CMD ["python", "/app/runtime.py"]