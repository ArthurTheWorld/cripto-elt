FROM apache/airflow:2.10.5-python3.12

# Bibliotecas do pipeline + dbt.
# O Airflow já traz requests e psycopg2; boto3 (storage S3) e dbt são nossos.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
