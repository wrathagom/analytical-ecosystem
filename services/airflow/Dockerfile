# Apache Airflow with Docker Provider
FROM apache/airflow:2.10.4-python3.12

USER root

# Install Docker CLI for DockerOperator
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install providers
RUN pip install --no-cache-dir \
    apache-airflow-providers-docker \
    apache-airflow-providers-postgres \
    apache-airflow-providers-mysql \
    apache-airflow-providers-redis \
    apache-airflow-providers-elasticsearch \
    apache-airflow-providers-http
