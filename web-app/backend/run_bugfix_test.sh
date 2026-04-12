#!/bin/bash

# Script to run bug condition exploration test for enrollment endpoint fix
# This script ensures services are running and executes the test

set -e

echo "========================================="
echo "Bug Condition Exploration Test Runner"
echo "========================================="
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    exit 1
fi

# Check if services are running
echo "Checking Docker services..."
if ! docker compose ps | grep -q "Up"; then
    echo "WARNING: Docker services may not be running"
    echo "Starting services..."
    docker compose up -d
    echo "Waiting for services to be ready..."
    sleep 10
fi

# Check if backend service is healthy
echo "Checking backend service..."
if ! docker compose ps backend | grep -q "Up"; then
    echo "ERROR: Backend service is not running"
    echo "Please start services with: docker compose up -d"
    exit 1
fi

# Check if postgres service is healthy
echo "Checking postgres service..."
if ! docker compose ps postgres | grep -q "Up"; then
    echo "ERROR: Postgres service is not running"
    echo "Please start services with: docker compose up -d"
    exit 1
fi

echo "✓ Services are running"
echo ""

# Install test dependencies
echo "Installing test dependencies..."
pip install -q pytest hypothesis httpx

echo "✓ Dependencies installed"
echo ""

# Run the test
echo "========================================="
echo "Running Bug Condition Exploration Tests"
echo "========================================="
echo ""
echo "IMPORTANT: These tests are EXPECTED TO FAIL on unfixed code."
echo "Test failures confirm the bug exists."
echo ""

cd "$(dirname "$0")"
pytest test_enrollment_bugfix.py -v --tb=short

TEST_EXIT_CODE=$?

echo ""
echo "========================================="
echo "Test Execution Complete"
echo "========================================="
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests PASSED"
    echo ""
    echo "This means either:"
    echo "  1. The bug has been fixed (expected after Task 3)"
    echo "  2. The bug doesn't exist (unexpected - may need to re-investigate)"
else
    echo "✗ Tests FAILED"
    echo ""
    echo "This is EXPECTED for bug condition exploration tests."
    echo "Test failures confirm the bug exists."
    echo ""
    echo "Next steps:"
    echo "  1. Review the test output above to see the counterexamples"
    echo "  2. Document the failures (they prove the bug exists)"
    echo "  3. Proceed to Task 2: Write preservation property tests"
    echo "  4. Proceed to Task 3: Implement the fix"
fi

exit $TEST_EXIT_CODE
