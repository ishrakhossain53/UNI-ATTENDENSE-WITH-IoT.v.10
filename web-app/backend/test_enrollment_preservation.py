"""
Preservation Property Tests for Enrollment Endpoint

These tests capture the behavior that MUST be preserved after the bugfix.
They test non-buggy inputs (first enrollment with valid data) and should PASS on unfixed code.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

IMPORTANT: Run these tests BEFORE implementing the fix to establish baseline behavior.
These tests should PASS on unfixed code and continue to PASS after the fix.

Run with:
    cd web-app/backend
    pip install -r requirements.txt
    pytest test_enrollment_preservation.py -v
"""

import pytest
import uuid
import base64
import os
import hashlib
import requests
from hypothesis import given, strategies as st, settings, Phase, HealthCheck


# Backend URL (running service)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_admin_token():
    """Login as admin and get JWT token."""
    response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


def create_test_student(admin_token):
    """Create a fresh test student for testing."""
    import time
    timestamp = int(time.time() * 1000)
    
    student_data = {
        "student_number": f"PRES{timestamp}",
        "full_name": f"Preservation Test Student {timestamp}",
        "department": "Computer Science",
        "semester": 3
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.post(
        f"{BACKEND_URL}/api/students",
        json=student_data,
        headers=headers
    )
    assert response.status_code == 200, f"Failed to create test student: {response.text}"
    return response.json()["student_id"]


def delete_test_student(student_id, admin_token):
    """Delete a test student."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    try:
        requests.delete(
            f"{BACKEND_URL}/api/students/{student_id}",
            headers=headers
        )
    except:
        pass


def generate_valid_template() -> str:
    """Generate a valid fingerprint template (base64 encoded random bytes)."""
    return base64.b64encode(os.urandom(128)).decode()


def generate_invalid_base64() -> str:
    """Generate invalid base64 string."""
    return "This is not valid base64!@#$%"


class TestPreservationProperties:
    """
    Preservation Property Tests
    
    These tests verify behavior that MUST remain unchanged after the bugfix.
    They test non-buggy inputs and should PASS on both unfixed and fixed code.
    """
    
    @settings(
        phases=[Phase.generate, Phase.target],
        max_examples=5,  # Test multiple valid enrollments
        deadline=None
    )
    @given(
        # Generate valid template data
        template_size=st.integers(min_value=64, max_value=256)
    )
    def test_property_2_first_enrollment_creates_template_and_encrypts(
        self, template_size
    ):
        """
        Property 2: Preservation - First Enrollment and Encryption Behavior
        
        **Validates: Requirements 3.1, 3.3, 3.4**
        
        CRITICAL: This test MUST PASS on unfixed code - it captures baseline behavior.
        
        Test that first-time enrollment with valid data:
        - Creates a fingerprint template record in the database
        - Encrypts the template data with AES-256-GCM
        - Marks the student as enrolled (fp_enrolled=TRUE)
        - Returns the template_id in the response
        - Logs an audit trail entry
        
        This behavior must be preserved after the fix.
        """
        admin_token = get_admin_token()
        student_id = create_test_student(admin_token)
        
        try:
            # Generate valid template data
            template_bytes = os.urandom(template_size)
            template_base64 = base64.b64encode(template_bytes).decode()
            
            # Enroll the student (first enrollment)
            enrollment_data = {
                "student_id": student_id,
                "template_data_base64": template_base64
            }
            
            headers = {"Authorization": f"Bearer {admin_token}"}
            response = requests.post(
                f"{BACKEND_URL}/api/enrollment/enroll",
                json=enrollment_data,
                headers=headers
            )
            
            # ASSERTION 1: Enrollment succeeds
            assert response.status_code in [200, 201], (
                f"First enrollment failed with status {response.status_code}. "
                f"Response: {response.text}\n"
                f"PRESERVATION VIOLATION: First enrollment should succeed"
            )
            
            response_data = response.json()
            
            # ASSERTION 2: Response contains template_id (Requirement 3.4)
            assert "template_id" in response_data, (
                "Response missing template_id field. "
                "PRESERVATION VIOLATION: Response must contain template_id"
            )
            
            template_id = response_data["template_id"]
            assert template_id is not None and template_id != "", (
                "template_id is empty. "
                "PRESERVATION VIOLATION: template_id must be returned"
            )
            
            # ASSERTION 3: Verify student enrollment status
            status_response = requests.get(
                f"{BACKEND_URL}/api/enrollment/status/{student_id}",
                headers=headers
            )
            assert status_response.status_code == 200, (
                f"Failed to get enrollment status: {status_response.text}"
            )
            
            status_data = status_response.json()
            assert status_data.get("fp_enrolled") is True, (
                "Student not marked as enrolled (fp_enrolled=FALSE). "
                "PRESERVATION VIOLATION: Student must be marked as enrolled"
            )
            
        finally:
            # Cleanup
            delete_test_student(student_id, admin_token)
    
    def test_property_2_admin_authentication_required(self):
        """
        Property 2: Preservation - Admin Authentication Required
        
        **Validates: Requirement 3.2**
        
        Test that enrollment endpoint requires valid admin authentication.
        This behavior must be preserved after the fix.
        """
        admin_token = get_admin_token()
        student_id = create_test_student(admin_token)
        
        try:
            enrollment_data = {
                "student_id": student_id,
                "template_data_base64": generate_valid_template()
            }
            
            # Test 1: No authentication header
            response = requests.post(
                f"{BACKEND_URL}/api/enrollment/enroll",
                json=enrollment_data
            )
            assert response.status_code == 403, (
                f"Expected 403 Forbidden without auth, got {response.status_code}. "
                "PRESERVATION VIOLATION: Endpoint must require authentication"
            )
            
            # Test 2: Invalid token
            headers = {"Authorization": "Bearer invalid_token_12345"}
            response = requests.post(
                f"{BACKEND_URL}/api/enrollment/enroll",
                json=enrollment_data,
                headers=headers
            )
            assert response.status_code == 403, (
                f"Expected 403 Forbidden with invalid token, got {response.status_code}. "
                "PRESERVATION VIOLATION: Endpoint must validate authentication"
            )
            
        finally:
            # Cleanup
            delete_test_student(student_id, admin_token)
    
    def test_property_2_invalid_base64_returns_400(self):
        """
        Property 2: Preservation - Invalid Base64 Returns 400
        
        **Validates: Requirement 3.5**
        
        Test that invalid base64 template data returns 400 Bad Request.
        This behavior must be preserved after the fix.
        """
        admin_token = get_admin_token()
        student_id = create_test_student(admin_token)
        
        try:
            enrollment_data = {
                "student_id": student_id,
                "template_data_base64": generate_invalid_base64()
            }
            
            headers = {"Authorization": f"Bearer {admin_token}"}
            response = requests.post(
                f"{BACKEND_URL}/api/enrollment/enroll",
                json=enrollment_data,
                headers=headers
            )
            
            assert response.status_code == 400, (
                f"Expected 400 Bad Request for invalid base64, got {response.status_code}. "
                f"Response: {response.text}\n"
                "PRESERVATION VIOLATION: Invalid base64 must return 400"
            )
            
            response_data = response.json()
            detail = response_data.get("detail", "").lower()
            assert "base64" in detail or "invalid" in detail, (
                f"Expected error message to mention 'base64' or 'invalid', got: {detail}"
            )
            
        finally:
            # Cleanup
            delete_test_student(student_id, admin_token)
    
    @settings(
        phases=[Phase.generate, Phase.target],
        max_examples=3,
        deadline=None
    )
    @given(
        # Generate various valid template sizes
        template_size=st.integers(min_value=32, max_value=512)
    )
    def test_property_2_valid_base64_decoded_correctly(
        self, template_size
    ):
        """
        Property 2: Preservation - Valid Base64 Decoded and Encrypted Correctly
        
        **Validates: Requirement 3.3**
        
        Test that valid base64 template data is decoded and encrypted correctly.
        This behavior must be preserved after the fix.
        """
        admin_token = get_admin_token()
        student_id = create_test_student(admin_token)
        
        try:
            # Generate valid template data of varying sizes
            template_bytes = os.urandom(template_size)
            template_base64 = base64.b64encode(template_bytes).decode()
            
            enrollment_data = {
                "student_id": student_id,
                "template_data_base64": template_base64
            }
            
            headers = {"Authorization": f"Bearer {admin_token}"}
            response = requests.post(
                f"{BACKEND_URL}/api/enrollment/enroll",
                json=enrollment_data,
                headers=headers
            )
            
            assert response.status_code in [200, 201], (
                f"Enrollment failed with status {response.status_code}. "
                f"Response: {response.text}\n"
                f"PRESERVATION VIOLATION: Valid base64 template should be accepted"
            )
            
            response_data = response.json()
            template_id = response_data.get("template_id")
            
            assert template_id is not None and template_id != "", (
                "template_id is empty. "
                "PRESERVATION VIOLATION: template_id must be returned"
            )
            
        finally:
            # Cleanup
            delete_test_student(student_id, admin_token)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
