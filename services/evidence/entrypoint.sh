#!/bin/bash
set -e

cd /evidence-workspace

if [ ! -f "package.json" ]; then
    echo "No Evidence project found. Initializing new project..."
    npx degit evidence-dev/template . --force
    npm install
fi

echo "Starting Evidence dev server..."
npm run sources && npm run dev -- --host 0.0.0.0
