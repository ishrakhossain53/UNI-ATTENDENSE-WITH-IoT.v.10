"""
Bug Condition Exploration Test for Enrollment Endpoint 500 Error Fix

This test is designed to FAIL on unfixed code to demonstrate the bug exists.
It tests the bug condition where enrolling a second student fails due to:
1. Hardcoded device_slot = 0 causing constraint violation
2. Missing database connection cleanup
3. Generic error handling returning 500 instead of specific status codes

**Validates: Requirements 1.1, 1.2, 1.3**

IMPORTANT: This test MUST be run with the Docker services running:
    docker compose up -d

Then run the test:
    cd web-app/backend
    pip install -r requirements.txt
    pytest test_enrollment_bugfix.py -v
"""

import pytest
import uuid
import base64
import os
from hypothesis import given, strategies as st, settings, Phase, HealthCheck
from fastapi.testclient import TestClient

# Import the FastAPI app
import sys
sys.path.insert(0, os.path.dirname(__file__))
from main import app, db_pool, create_jwt


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_token():
    """Create admin JWT token for testing."""
    # Use the seeded admin user from init.sql
    # Username: admin, password: admin123
    # We'll create a token directly since we know the user_id from the seed data
    # For testing, we'll use a mock user_id
    return create_jwt("00000000-0000-0000-0000-000000000001", "admin", "admin")


@pytest.fixture(scope="function")
def test_students(client, admin_token):
    """Create test students for enrollment testing."""
    students = []
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create unique test students for each test run
    import time
    timestamp = int(time.time() * 1000)
    
    for i in range(3):
        student_data = {
            "student_number": f"TEST{timestamp}{i:03d}",
            "full_name": f"Test Student {timestamp}-{i}",
            "department": "Computer Science",
            "semester": 3
        }
        response = client.post("/api/students", json=student_data, headers=headers)
        if response.status_code == 200:
            students.append(response.json()["student_id"])
    
    yield students
    
    # Cleanup: deactivate test students
    for student_id in students:
        try:
            client.delete(f"/api/students/{student_id}", headers=headers)
        except:
            pass


def generate_fake_template() -> str:
    """Generate a fake fingerprint template (base64 encoded random bytes)."""
    return base64.b64encode(os.urandom(128)).decode()


class TestBugConditionExploration:
    """
    Bug Condition Exploration Tests
    
    These tests are EXPECTED TO FAIL on unfixed code.
    Failure confirms the bug exists.
    
    CRITICAL: This is a bugfix spec exploration test.
    When this test FAILS, it means the bug exists (SUCCESS for exploration).
    When this test PASSES, it means the bug is fixed (or doesn't exist).
    """
    
    @settings(
        phases=[Phase.generate, Phase.target],
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=1,  # Scoped to concrete failing case
        deadline=None
    )
    @given(
        # Scoped PBT: Generate exactly 2 enrollment attempts to reproduce the bug
        num_enrollments=st.just(2)
    )
    def test_property_1_second_enrollment_constraint_violation(
        self, client, admin_token, test_students, num_enrollments
    ):
        """
        Property 1: Bug Condition - Second Enrollment Constraint Violation
        
        **Validates: Requirements 1.1, 1.2, 1.3**
        
        CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
        
        Test that enrolling a second student succeeds with auto-assigned device_slot.
        On unfixed code, this will fail because device_slot is hardcoded to 0.
        
        Expected behavior (after fix):
        - First enrollment: device_slot = 0, returns 200/201
        - Second enrollment: device_slot = 1, returns 200/201
        - Device slots are auto-assigned sequentially
        
        Actual behavior (unfixed code):
        - First enrollment: device_slot = 0, returns 200/201
        - Second enrollment: device_slot = 0, returns 500 (constraint violation)
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Ensure we have enough test students
        assert len(test_students) >= num_enrollments, "Not enough test students created"
        
        enrollment_results = []
        device_slots = []
        
        # Attempt to enroll multiple students sequentially
        for i in range(num_enrollments):
            student_id = test_students[i]
            enrollment_data = {
                "student_id": student_id,
                "template_data_base64": generate_fake_template()
            }
            
            response = client.post("/api/enrollment/enroll", json=enrollment_data, headers=headers)
            enrollment_results.append({
                "student_index": i,
                "student_id": student_id,
                "status_code": response.status_code,
                "response": response.json() if response.status_code in [200, 201] else response.text
            })
            
            # If enrollment succeeded, query the device_slot
            if response.status_code in [200, 201] and db_pool:
                try:
                    conn = db_pool.get_conn()
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT device_slot FROM fingerprint_templates WHERE student_id = %s AND is_active = TRUE ORDER BY enrolled_at DESC LIMIT 1",
                        (student_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        device_slots.append(row[0])
                    cur.close()
                    db_pool.put_conn(conn)
                except Exception as e:
                    print(f"Error querying device_slot: {e}")
        
        # ASSERTIONS: Expected behavior after fix
        
        # 1. All enrollments should succeed (no 500 errors)
        for result in enrollment_results:
            assert result["status_code"] in [200, 201], (
                f"Enrollment {result['student_index']} for student {result['student_id']} "
                f"failed with status {result['status_code']}. "
                f"Expected 200/201. Response: {result['response']}\n"
                f"BUG DETECTED: Second enrollment fails with constraint violation due to hardcoded device_slot=0"
            )
        
        # 2. Verify device_slot values are unique and sequential
        assert len(device_slots) == num_enrollments, (
            f"Expected {num_enrollments} device slots, got {len(device_slots)}"
        )
        
        # Check that device slots are unique
        assert len(set(device_slots)) == len(device_slots), (
            f"Device slots are not unique: {device_slots}. "
            f"BUG DETECTED: Hardcoded device_slot=0 causes duplicate values"
        )
        
        # Check that device slots are sequential (allowing for existing templates)
        # They should be increasing
        for i in range(1, len(device_slots)):
            assert device_slots[i] > device_slots[i-1], (
                f"Device slots are not sequential: {device_slots}. "
                f"Expected each slot to be greater than the previous."
            )
    
    def test_invalid_uuid_returns_400(self, client, admin_token):
        """
        Test that invalid UUID format returns 400 Bad Request (not 500).
        
        **Validates: Requirement 1.3**
        
        Expected behavior (after fix): 400 Bad Request
        Actual behavior (unfixed code): 500 Internal Server Error
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        enrollment_data = {
            "student_id": "not-a-valid-uuid",
            "template_data_base64": generate_fake_template()
        }
        
        response = client.post("/api/enrollment/enroll", json=enrollment_data, headers=headers)
        
        # After fix, should return 400 Bad Request
        assert response.status_code == 400, (
            f"Expected 400 Bad Request for invalid UUID, got {response.status_code}. "
            f"Response: {response.text}\n"
            f"BUG DETECTED: Invalid UUID returns 500 instead of 400"
        )
        
        response_data = response.json()
        detail = response_data.get("detail", "").lower()
        assert "invalid" in detail or "uuid" in detail or "format" in detail, (
            f"Expected error message to mention 'invalid', 'uuid', or 'format', got: {detail}"
        )
    
    def test_nonexistent_student_returns_404(self, client, admin_token):
        """
        Test that non-existent student_id returns 404 Not Found (not 500).
        
        **Validates: Requirement 1.3**
        
        Expected behavior (after fix): 404 Not Found
        Actual behavior (unfixed code): 500 Internal Server Error (or constraint violation)
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Generate a valid UUID that doesn't exist in the database
        nonexistent_id = str(uuid.uuid4())
        
        enrollment_data = {
            "student_id": nonexistent_id,
            "template_data_base64": generate_fake_template()
        }
        
        response = client.post("/api/enrollment/enroll", json=enrollment_data, headers=headers)
        
        # After fix, should return 404 Not Found
        assert response.status_code == 404, (
            f"Expected 404 Not Found for non-existent student, got {response.status_code}. "
            f"Response: {response.text}\n"
            f"BUG DETECTED: Non-existent student returns {response.status_code} instead of 404"
        )
        
        response_data = response.json()
        detail = response_data.get("detail", "").lower()
        assert "not found" in detail or "student" in detail, (
            f"Expected error message to mention 'not found' or 'student', got: {detail}"
        )
    
    def test_connection_cleanup_after_exception(self, client, admin_token):
        """
        Test that database connection is properly returned to pool after exceptions.
        
        **Validates: Requirement 1.2**
        
        Expected behavior (after fix): Connection returned to pool in finally block
        Actual behavior (unfixed code): Connection not returned, pool exhaustion risk
        """
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Track connection pool size
        initial_pool_size = None
        if db_pool:
            try:
                conn = db_pool.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'active'")
                initial_pool_size = cur.fetchone()[0]
                cur.close()
                db_pool.put_conn(conn)
            except Exception as e:
                print(f"Could not get initial pool size: {e}")
        
        # Trigger multiple errors to test connection cleanup
        error_count = 5
        for i in range(error_count):
            enrollment_data = {
                "student_id": "invalid-uuid-format",
                "template_data_base64": generate_fake_template()
            }
            response = client.post("/api/enrollment/enroll", json=enrollment_data, headers=headers)
            # We expect errors here, that's the point
        
        # Check connection pool size after errors
        final_pool_size = None
        if db_pool and initial_pool_size is not None:
            try:
                conn = db_pool.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'active'")
                final_pool_size = cur.fetchone()[0]
                cur.close()
                db_pool.put_conn(conn)
            except Exception as e:
                print(f"Could not get final pool size: {e}")
        
        # Pool size should remain stable (connections properly returned)
        if initial_pool_size is not None and final_pool_size is not None:
            # Allow some variance for test connections, but not error_count connections leaked
            max_acceptable_growth = 3
            actual_growth = final_pool_size - initial_pool_size
            
            assert actual_growth <= max_acceptable_growth, (
                f"Connection pool size grew from {initial_pool_size} to {final_pool_size} "
                f"(+{actual_growth} connections) after {error_count} errors. "
                f"Expected growth <= {max_acceptable_growth}.\n"
                f"BUG DETECTED: Connections not properly cleaned up after exceptions"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
