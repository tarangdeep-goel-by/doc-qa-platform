#!/bin/bash

###############################################################################
# Run tests in Docker container
# This script runs the pytest suite inside the Docker environment
###############################################################################

set -e

echo "=== Running Backend Tests in Docker ==="
echo ""

# Check if backend is running
if ! docker ps | grep -q doc-qa-backend; then
    echo "Error: Backend container is not running"
    echo "Start services first with: docker-compose up -d"
    exit 1
fi

# Run tests
docker-compose run --rm test

echo ""
echo "=== Tests Complete ==="
