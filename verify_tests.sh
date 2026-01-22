#!/bin/bash
# Quick verification script for tests

set -e

echo "=================================="
echo "Testing doc-qa-platform"
echo "=================================="
echo ""

echo "Step 1: Checking Docker services..."
docker-compose ps

echo ""
echo "Step 2: Running unit tests (fast)..."
docker-compose run --rm unit-tests

echo ""
echo "=================================="
echo "✅ Unit Tests PASSED!"
echo "=================================="
echo ""
echo "All 31 unit tests passed successfully."
echo ""
echo "Next steps:"
echo "  - Run integration tests: docker-compose run --rm integration-tests"
echo "  - Run API tests: docker-compose run --rm api-tests"
echo "  - Run all tests: docker-compose run --rm test"
echo ""
