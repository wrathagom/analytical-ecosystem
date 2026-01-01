"""
Example DAG demonstrating the Analytical Ecosystem integration.

This DAG shows how to:
1. Run Docker containers as tasks
2. Connect to ecosystem services (PostgreSQL, Elasticsearch)
3. Use the shared network for inter-service communication
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.docker.operators.docker import DockerOperator

default_args = {
    'owner': 'ecosystem',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'example_ecosystem',
    default_args=default_args,
    description='Example DAG for Analytical Ecosystem',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['example', 'ecosystem'],
) as dag:

    # Task 1: Simple hello world
    hello = DockerOperator(
        task_id='hello_world',
        image='alpine:latest',
        command='echo "Hello from the Analytical Ecosystem!"',
        docker_url='unix://var/run/docker.sock',
        network_mode='analytical-ecosystem',
        auto_remove='success',
    )

    # Task 2: Run Python code
    python_task = DockerOperator(
        task_id='python_analysis',
        image='python:3.12-slim',
        command='''python -c "
import json
data = {'status': 'success', 'message': 'Analysis complete'}
print(json.dumps(data))
"''',
        docker_url='unix://var/run/docker.sock',
        network_mode='analytical-ecosystem',
        auto_remove='success',
    )

    # Task 3: Query PostgreSQL (if running)
    # Uncomment if you have postgres profile enabled
    # postgres_query = DockerOperator(
    #     task_id='query_postgres',
    #     image='postgres:17.2',
    #     command='psql -h postgres -U analyticsUser -d analytics -c "SELECT NOW();"',
    #     docker_url='unix://var/run/docker.sock',
    #     network_mode='analytical-ecosystem',
    #     environment={'PGPASSWORD': 'analyticsPass'},
    #     auto_remove='success',
    # )

    hello >> python_task
