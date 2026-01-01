#!/bin/sh
# Metabase auto-setup script
# Waits for Metabase to start, then calls the setup API if needed

METABASE_URL="${METABASE_URL:-http://metabase:3000}"
ADMIN_EMAIL="${MB_ADMIN_EMAIL:-admin@localhost}"
ADMIN_PASSWORD="${MB_ADMIN_PASSWORD:-ecosystem}"
ADMIN_FIRST="${MB_ADMIN_FIRST_NAME:-Admin}"
ADMIN_LAST="${MB_ADMIN_LAST_NAME:-User}"
SITE_NAME="${MB_SITE_NAME:-Analytical Ecosystem}"

echo "Waiting for Metabase to be ready..."

# Wait for Metabase to respond
i=0
while [ $i -lt 60 ]; do
    i=$((i + 1))
    if curl -s "$METABASE_URL/api/health" | grep -q "ok"; then
        echo "Metabase is healthy"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "Metabase failed to start"
        exit 1
    fi
    echo "Attempt $i/60: Metabase not ready yet..."
    sleep 5
done

# Get session properties to check setup status and get token
PROPS=$(curl -s "$METABASE_URL/api/session/properties")

# Check if setup is still needed
if ! echo "$PROPS" | grep -q '"has-user-setup":false'; then
    echo "Metabase already configured, skipping setup"
    exit 0
fi

# Extract setup token from properties
SETUP_TOKEN=$(echo "$PROPS" | grep -o '"setup-token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$SETUP_TOKEN" ]; then
    echo "Could not retrieve setup token"
    exit 1
fi

echo "Running initial setup..."

# Call the setup API
RESPONSE=$(curl -s -X POST "$METABASE_URL/api/setup" \
    -H "Content-Type: application/json" \
    -d "{
        \"token\": \"$SETUP_TOKEN\",
        \"user\": {
            \"email\": \"$ADMIN_EMAIL\",
            \"password\": \"$ADMIN_PASSWORD\",
            \"first_name\": \"$ADMIN_FIRST\",
            \"last_name\": \"$ADMIN_LAST\",
            \"site_name\": \"$SITE_NAME\"
        },
        \"prefs\": {
            \"site_name\": \"$SITE_NAME\",
            \"allow_tracking\": false
        }
    }")

if echo "$RESPONSE" | grep -q "id"; then
    echo "Setup completed successfully!"
    echo "Admin user: $ADMIN_EMAIL"
else
    echo "Setup failed: $RESPONSE"
    exit 1
fi
