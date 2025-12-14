import os
import time
from flask import Flask
import redis

app = Flask(__name__)

# конфиги из переменных окружения (ConfigMap/Secret)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
SECRET_KEY = os.getenv('APP_SECRET', 'default-secret')

# Подключение к Redis
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

@app.route('/')
def hello():
    count = get_hit_count()
    pod_name = os.getenv('HOSTNAME', 'unknown-pod')
    return f'Hello from Pod: {pod_name}! I have been seen {count} times. Secret is: {SECRET_KEY}\n'

# Проба для Liveness/Readiness
@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
