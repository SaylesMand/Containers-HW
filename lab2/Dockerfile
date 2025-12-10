# FROM apache/airflow:slim-3.1.3-python3.12
FROM apache/airflow:3.1.3-python3.12


USER root


RUN apt-get update \
    && apt-get install -y --no-install-recommends vim htop \
    && rm -rf /var/lib/apt/lists/*

    
USER airflow


WORKDIR /opt/airflow

CMD ["airflow", "standalone"]