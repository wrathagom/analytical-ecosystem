FROM n8nio/n8n:latest

USER root

# Install Python 3 (try apt for Debian-based, fall back to apk for Alpine)
RUN if command -v apt-get > /dev/null; then \
        apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*; \
    elif command -v apk > /dev/null; then \
        apk add --no-cache python3 py3-pip; \
    fi

USER node
