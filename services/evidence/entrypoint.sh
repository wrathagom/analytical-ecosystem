#!/bin/bash
set -e

cd /evidence-workspace

if [ ! -f "package.json" ]; then
    echo "No Evidence project found. Initializing new project..."
    npx degit evidence-dev/template . --force
    npm install
fi

# Fix permissions for Jupyter compatibility (jovyan user is UID 1000)
echo "Setting file permissions for cross-service editing..."
chown -R 1000:1000 /evidence-workspace

echo "Starting Evidence dev server..."
npm run sources && npm run dev -- --host 0.0.0.0
