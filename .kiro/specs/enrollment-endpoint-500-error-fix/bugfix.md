# Bugfix Requirements Document

## Introduction

The enrollment endpoint `POST /api/enrollment/enroll` is returning 500 (Internal Server Error) when attempting to enroll students with fingerprint templates. This bug prevents administrators from enrolling students in the attendance system, which is a critical feature for the application. The error occurs consistently after the first successful enrollment, suggesting a database constraint violation or resource management issue in the backend enrollment logic.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN an admin attempts to enroll a second student with a fingerprint template THEN the system returns a 500 Internal Server Error due to a database constraint violation on the hardcoded device_slot value

1.2 WHEN a database exception occurs during enrollment THEN the system fails to properly clean up the database connection, potentially exhausting the connection pool

1.3 WHEN the enrollment endpoint encounters any error THEN the system returns a generic "Internal server error" message without exposing the specific error details to help diagnose the issue

### Expected Behavior (Correct)

2.1 WHEN an admin attempts to enroll any student with a fingerprint template THEN the system SHALL automatically assign the next available device_slot value to avoid conflicts

2.2 WHEN a database exception occurs during enrollment THEN the system SHALL properly return the database connection to the pool using a finally block or context manager

2.3 WHEN the enrollment endpoint encounters a database constraint violation THEN the system SHALL return a 409 Conflict status with a descriptive error message indicating the specific constraint that was violated

2.4 WHEN the enrollment endpoint encounters an invalid student_id format THEN the system SHALL return a 400 Bad Request status with a message indicating the UUID format is invalid

2.5 WHEN the enrollment endpoint encounters a non-existent student_id THEN the system SHALL return a 404 Not Found status with a message indicating the student was not found

### Unchanged Behavior (Regression Prevention)

3.1 WHEN an admin successfully enrolls a student for the first time THEN the system SHALL CONTINUE TO create a fingerprint template record, encrypt the template data with AES-256-GCM, and mark the student as enrolled

3.2 WHEN the enrollment endpoint receives valid authentication credentials with admin role THEN the system SHALL CONTINUE TO allow access to the endpoint

3.3 WHEN the enrollment endpoint receives a valid base64-encoded template THEN the system SHALL CONTINUE TO decode and encrypt the template data correctly

3.4 WHEN the enrollment endpoint successfully completes THEN the system SHALL CONTINUE TO log the audit trail and return the template_id in the response

3.5 WHEN the enrollment endpoint receives invalid base64 data THEN the system SHALL CONTINUE TO return a 400 Bad Request error
