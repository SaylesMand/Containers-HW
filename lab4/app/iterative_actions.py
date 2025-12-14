# Лабораторная работа выполнялась на MacOS

# 1. Запуск minikube
minikube start

# 2. Создание папок
mkdir -p lab4/app
cd lab4

# 2.1 Создание requirements
cat <<EOF > app/requirements.txt
flask
redis
EOF

# 2.2. Создание app.py
cat <<EOF > app/app.py
import os
import time
from flask import Flask
import redis

app = Flask(__name__)

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
SECRET_KEY = os.getenv('APP_SECRET', 'default-secret')

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

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
EOF

# 2.3 Создание Dockerfile
cat <<EOF > app/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN mkdir /app/logs

EXPOSE 5000

CMD ["python", "app.py"]
EOF

# 3. Создание манифестов
cat <<EOF > k8s-manifests.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  labels:
    component: config
data:
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
  labels:
    component: security
type: Opaque
stringData:
  APP_SECRET: "MacUserSecret123"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-deployment
  labels:
    app: redis
    tier: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:alpine
        ports:
        - containerPort: 6379
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
    - protocol: TCP
      port: 6379
      targetPort: 6379
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-app-deployment
  labels:
    app: flask-app
    tier: frontend
    student: lab-work
spec:
  replicas: 2
  selector:
    matchLabels:
      app: flask-app
  template:
    metadata:
      labels:
        app: flask-app
    spec:
      initContainers:
      - name: init-redis
        image: busybox:1.28
        command: ['sh', '-c', "until nslookup redis-service.\$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace).svc.cluster.local; do echo waiting for redis; sleep 2; done"]
          # экранирование $ в init-контейнере как \$, чтобы bash не попытался подставить переменную прямо сейчас
      containers:
      - name: flask-app
        image: my-flask-app:v1
        imagePullPolicy: Never
        ports:
        - containerPort: 5000
        env:
          - name: REDIS_HOST
            valueFrom:
              configMapKeyRef:
                name: app-config
                key: REDIS_HOST
          - name: REDIS_PORT
            valueFrom:
              configMapKeyRef:
                name: app-config
                key: REDIS_PORT
          - name: APP_SECRET
            valueFrom:
              secretKeyRef:
                name: app-secret
                key: APP_SECRET
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: logs-volume
          mountPath: /app/logs
      volumes:
      - name: logs-volume
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: flask-service
spec:
  selector:
    app: flask-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
      nodePort: 30001
  type: NodePort
EOF

# 4. Сборка образа
eval $(minikube docker-env)
docker build -t my-flask-app:v1 ./app

# 5. Запуск в Kubernetes
kubectl apply -f k8s-manifests.yaml
kubectl get pods -w

# 6. Доступ к сайту
# На macOS нельзя просто обратиться по IP-адресу ноды, так как Docker Desktop изолирует сеть.
# Minikube сам создаст туннель и откроет браузер.
minikube service flask-service
