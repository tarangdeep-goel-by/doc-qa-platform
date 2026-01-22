#!/bin/bash
# Quick script to rebuild Docker and run tests

set -e  # Exit on error

echo "=== Rebuilding Docker Images ==="
docker-compose build backend

echo ""
echo "=== Starting Services ==="
docker-compose up -d qdrant backend

echo ""
echo "Waiting for services to be ready..."
sleep 5

echo ""
echo "=== Running Tests ==="
docker-compose run --rm test

echo ""
echo "=== Test Results Above ==="
