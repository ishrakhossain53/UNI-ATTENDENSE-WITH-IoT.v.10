# Bug Condition Exploration Test - Enrollment Endpoint 500 Error Fix

## Overview

This test suite validates the bug condition for the enrollment endpoint 500 error fix. The tests are designed to **FAIL on unfixed code** to demonstrate that the bug exists.

## Bug Description

The enrollment endpoint `POST /api/enrollment/enroll` has three issues:

1. **Hardcoded device_slot = 0**: Causes constraint violation when enrolling a second student
2. **Missing connection cleanup**: Database connections not returned to pool after exceptions
3. **Generic error handling**: Returns 500 for all errors instead of specific status codes (400, 404, 409)

## Prerequisites

1. Docker and Docker Compose installed
2. Python 3.9+ installed
3. All services running

## Setup Instructions

### 1. Start Docker Services

```bash
# From project root
docker compose up -d

# Verify services are running
docker compose ps
```

### 2. Install Test Dependencies

```bash
cd web-app/backend
pip install -r requirements.txt
```

## Running the Tests

### Run All Tests

```bash
cd web-app/backend
pytest test_enrollment_bugfix.py -v
```

### Run Specific Test

```bash
# Test second enrollment constraint violation
pytest test_enrollment_bugfix.py::TestBugConditionExploration::test_property_1_second_enrollment_constraint_violation -v

# Test invalid UUID handling
pytest test_enrollment_bugfix.py::TestBugConditionExploration::test_invalid_uuid_returns_400 -v

# Test non-existent student handling
pytest test_enrollment_bugfix.py::TestBugConditionExploration::test_nonexistent_student_returns_404 -v

# Test connection cleanup
pytest test_enrollment_bugfix.py::TestBugConditionExploration::test_connection_cleanup_after_exception -v
```

### Run with Verbose Output

```bash
pytest test_enrollment_bugfix.py -v --tb=short
```

## Expected Test Results

### On UNFIXED Code (Current State)

All tests should **FAIL**, demonstrating the bug exists:

1. ✗ `test_property_1_second_enrollment_constraint_violation` - Second enrollment fails with 500 error
2. ✗ `test_invalid_uuid_returns_400` - Invalid UUID returns 500 instead of 400
3. ✗ `test_nonexistent_student_returns_404` - Non-existent student returns 500 instead of 404
4. ✗ `test_connection_cleanup_after_exception` - Connection pool grows after exceptions

### After Fix Implementation

All tests should **PASS**, confirming the bug is fixed:

1. ✓ `test_property_1_second_enrollment_constraint_violation` - Second enrollment succeeds with auto-assigned device_slot
2. ✓ `test_invalid_uuid_returns_400` - Invalid UUID returns 400 Bad Request
3. ✓ `test_nonexistent_student_returns_404` - Non-existent student returns 404 Not Found
4. ✓ `test_connection_cleanup_after_exception` - Connection pool remains stable

## Test Details

### Property 1: Second Enrollment Constraint Violation

**Validates: Requirements 1.1, 1.2, 1.3**

This property-based test uses Hypothesis to generate enrollment scenarios. It's scoped to the concrete failing case (2 enrollments) to ensure reproducibility.

**What it tests:**
- Enrolling two students sequentially
- Verifying device_slot values are unique and sequential
- Confirming no 500 errors occur

**Expected failure on unfixed code:**
```
AssertionError: Enrollment 1 for student <uuid> failed with status 500.
Expected 200/201. Response: Internal server error
BUG DETECTED: Second enrollment fails with constraint violation due to hardcoded device_slot=0
```

### Test: Invalid UUID Returns 400

**Validates: Requirement 1.3**

**What it tests:**
- Sending enrollment request with malformed student_id
- Verifying 400 Bad Request is returned (not 500)

**Expected failure on unfixed code:**
```
AssertionError: Expected 400 Bad Request for invalid UUID, got 500.
BUG DETECTED: Invalid UUID returns 500 instead of 400
```

### Test: Non-existent Student Returns 404

**Validates: Requirement 1.3**

**What it tests:**
- Sending enrollment request with valid UUID but non-existent student
- Verifying 404 Not Found is returned (not 500)

**Expected failure on unfixed code:**
```
AssertionError: Expected 404 Not Found for non-existent student, got 500.
BUG DETECTED: Non-existent student returns 500 instead of 404
```

### Test: Connection Cleanup After Exception

**Validates: Requirement 1.2**

**What it tests:**
- Triggering multiple errors during enrollment
- Monitoring database connection pool size
- Verifying connections are returned to pool

**Expected failure on unfixed code:**
```
AssertionError: Connection pool size grew from 5 to 10 (+5 connections) after 5 errors.
Expected growth <= 3.
BUG DETECTED: Connections not properly cleaned up after exceptions
```

## Troubleshooting

### Services Not Running

```bash
# Check service status
docker compose ps

# View logs
docker compose logs backend
docker compose logs postgres

# Restart services
docker compose restart
```

### Database Connection Issues

```bash
# Check if PostgreSQL is accepting connections
docker compose exec postgres psql -U attendance_user -d attendance_db -c "SELECT 1"

# Check backend logs
docker compose logs backend
```

### Test Failures

If tests fail for unexpected reasons:

1. Ensure all services are running: `docker compose ps`
2. Check backend logs: `docker compose logs backend`
3. Verify database is initialized: `docker compose logs postgres | grep "database system is ready"`
4. Restart services: `docker compose restart`

## Next Steps

After running these tests and confirming they FAIL on unfixed code:

1. Document the counterexamples found
2. Proceed to Task 2: Write preservation property tests
3. Implement the fix in Task 3
4. Re-run these tests to verify the fix works

## Notes

- These tests use property-based testing with Hypothesis for stronger guarantees
- The tests are scoped to concrete failing cases for deterministic bug reproduction
- Connection pool monitoring may show some variance due to test infrastructure
- Tests create and clean up their own test data to avoid interference
