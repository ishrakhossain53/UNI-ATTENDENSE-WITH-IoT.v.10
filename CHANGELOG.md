# Changelog

All notable changes to the University Attendance Tracking System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-11

### Added
- **Enrollment Revoke Functionality**
  - Admin can now revoke student fingerprint enrollment
  - Added `DELETE /api/enrollment/revoke/{student_id}` endpoint
  - Updated enrollment dialog to show revoke confirmation
  - Added warning message when revoking enrollment
  
- **Attendance Record Management**
  - Admin can edit attendance records (status, timestamp, verification method)
  - Admin can delete attendance records with confirmation dialog
  - Admin/Faculty can manually add attendance records
  - Added `PUT /api/attendance/{record_id}` endpoint
  - Added `DELETE /api/attendance/{record_id}` endpoint
  - Added `POST /api/attendance/manual` endpoint
  - Added Edit and Delete buttons in Past Attendance tab
  - Added attendance edit dialog with form validation

- **Testing Infrastructure**
  - Comprehensive property-based testing suite using Hypothesis
  - Bug condition exploration tests (`test_enrollment_bugfix.py`)
  - Preservation property tests (`test_enrollment_preservation.py`)
  - Test runner script (`run_bugfix_test.sh`)
  - Testing documentation (`TEST_README.md`)

- **Documentation**
  - Added `.env.example` with comprehensive configuration guide
  - Added production deployment checklist
  - Added `CHANGELOG.md` for version tracking
  - Updated README with new features and API endpoints
  - Added project structure diagram
  - Added testing section

### Fixed
- **Enrollment Endpoint 500 Error** (Critical Bug)
  - Fixed hardcoded `device_slot = 0` causing constraint violations on second enrollment
  - Implemented auto-assignment of device_slot using `MAX(device_slot) + 1`
  - Added database connection cleanup in finally blocks
  - Replaced generic 500 errors with specific HTTP status codes:
    - 400 Bad Request for invalid UUID format
    - 404 Not Found for non-existent student
    - 409 Conflict for constraint violations
  - Added JWT user_id validation before foreign key operations
  - Updated database schema with `ON DELETE SET NULL` for enrolled_by foreign key

### Changed
- Enhanced error handling across all enrollment endpoints
- Improved frontend enrollment dialog UX
- Updated API documentation with new endpoints
- Restructured .env file with clear sections and comments
- Updated README with emoji icons and better organization

### Security
- Added audit logging for attendance record modifications
- Added admin-only authorization checks for sensitive operations
- Improved input validation for attendance record updates

## [1.0.0] - 2026-04-01

### Added
- Initial release of University Attendance Tracking System
- ESP32 device simulator with 5 classroom units
- MQTT gateway service for device-to-cloud communication
- FastAPI backend with JWT authentication
- React frontend with Material-UI
- PostgreSQL database with monthly partitioning
- Redis for session management and caching
- WebSocket real-time attendance updates
- Role-based access control (Admin, Faculty, Student)
- Fingerprint enrollment system
- Attendance reporting and analytics
- At-risk student identification
- Device management dashboard
- Audit logging system
- Docker Compose orchestration

### Features
- Real-time attendance tracking with sub-3 second latency
- AES-256-GCM encryption for biometric data
- Offline queue for gateway when backend unavailable
- Automatic fingerprint template synchronization
- Per-student and per-course attendance reports
- CSV export functionality
- Live attendance feed with WebSocket
- Attendance threshold configuration
- Device battery monitoring
- Classroom management

---

## Version History

- **1.1.0** (2026-04-11) - Enrollment revoke, attendance management, bug fixes
- **1.0.0** (2026-04-01) - Initial release

## Upgrade Guide

### From 1.0.0 to 1.1.0

1. **Backup your database**:
   ```bash
   docker compose exec postgres pg_dump -U attendance_user attendance_db > backup.sql
   ```

2. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

3. **Rebuild containers**:
   ```bash
   docker compose down
   docker compose up -d --build
   ```

4. **Verify new endpoints**:
   ```bash
   curl http://localhost:8000/openapi.json | grep attendance
   ```

5. **Test new features**:
   - Login as admin
   - Try revoking a student enrollment
   - Edit an attendance record in Past Attendance tab
   - Delete an attendance record

No database migrations required for this update.

## Support

For issues, questions, or contributions, please refer to the project repository.
