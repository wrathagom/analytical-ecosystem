# Jupyter Data Science Notebook
# Based on the official Jupyter Docker Stacks
ARG BASE_IMAGE=quay.io/jupyter/datascience-notebook:2025-12-22
FROM $BASE_IMAGE

# Switch to root to copy file with proper permissions
USER root
COPY requirements.txt /tmp/requirements.txt
RUN chmod 644 /tmp/requirements.txt

# Switch back to jovyan user
USER ${NB_UID}

# Install additional Python packages
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install JupyterLab extensions
RUN pip install --no-cache-dir ipydrawio
