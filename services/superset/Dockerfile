FROM apache/superset:4.1.1

# Install PostgreSQL driver for connecting to external PostgreSQL databases
USER root
RUN pip install --no-cache-dir psycopg2-binary
USER superset
