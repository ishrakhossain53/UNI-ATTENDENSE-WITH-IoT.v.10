# University Attendance Tracking System

A distributed three-tier attendance tracking system for universities using ESP32 fingerprint scanners, MQTT gateway, PostgreSQL database, and a full-stack web application.

## 🎯 Key Features

- **Real-Time Attendance Tracking**: MQTT-based device-to-gateway-to-backend pipeline (sub-3 second latency)
- **Biometric Authentication**: Fingerprint-based student identification with AES-256-GCM encryption
- **Role-Based Access Control**: Admin, Faculty, and Student dashboards with granular permissions
- **Live WebSocket Updates**: Instant attendance notifications across all connected clients
- **Attendance Management**: Edit, delete, and manually add attendance records (Admin only)
- **Enrollment Management**: Enroll and revoke student fingerprint templates (Admin only)
- **Comprehensive Reporting**: Per-student, per-course analytics with CSV export
- **At-Risk Student Alerts**: Automatic identification of students below attendance threshold
- **Offline Queue**: Gateway queues scans when backend is unavailable
- **Audit Logging**: Complete audit trail of all system actions

## 🏗️ Architecture

```
ASE/
├── .env                          # Environment configuration
├── docker-compose.yml            # Docker orchestration
├── README.md                     # This file
│
├── .kiro/                        # Kiro AI specs and configurations
│   └── specs/
│       └── enrollment-endpoint-500-error-fix/
│           ├── bugfix.md         # Bug condition documentation
│           ├── design.md         # Fix design document
│           └── tasks.md          # Implementation tasks
│
├── attendance-device/            # ESP32 Device Simulator
│   ├── Dockerfile
│   ├── esp_emulator.py          # Simulates 5 ESP32 fingerprint scanners
│   └── requirements.txt
│
├── gateway/                      # MQTT-to-REST Gateway Service
│   ├── Dockerfile
│   ├── gateway_service.py       # Bridges MQTT and backend API
│   └── requirements.txt
│
├── database/                     # PostgreSQL Database
│   └── init.sql                 # Schema, seed data, partitions
│
├── mosquitto/                    # MQTT Broker Configuration
│   └── config/
│       └── mosquitto.conf       # MQTT broker settings
│
└── web-app/                      # Full-Stack Web Application
    ├── backend/                  # FastAPI Backend
    │   ├── Dockerfile
    │   ├── main.py              # API endpoints, WebSocket, auth
    │   ├── requirements.txt
    │   ├── test_enrollment_bugfix.py        # Bug condition tests
    │   ├── test_enrollment_preservation.py  # Preservation tests
    │   ├── run_bugfix_test.sh              # Test runner script
    │   ├── TEST_README.md                   # Testing documentation
    │   └── TASK1_SUMMARY.md                 # Bugfix implementation summary
    │
    └── frontend/                 # React Frontend
        ├── Dockerfile
        ├── nginx.conf           # Nginx reverse proxy config
        ├── package.json
        ├── vite.config.js
        ├── index.html
        └── src/
            ├── index.jsx        # App entry point
            ├── App.jsx          # Main app component
            ├── api.jsx          # Axios API client
            ├── store.jsx        # Zustand state management
            └── components/
                ├── Login.jsx              # Login page
                ├── AdminDashboard.jsx     # Admin dashboard
                ├── FacultyDashboard.jsx   # Faculty dashboard
                └── StudentDashboard.jsx   # Student dashboard
```

```
ESP32 Devices (Simulated)
    ↓ MQTT (encrypted)
Raspberry Pi Gateway
    ↓ REST API + JWT
FastAPI Backend
    ↓ SQL + WebSocket
React Frontend + PostgreSQL + Redis + MQTT Broker
```

### Components

1. **ESP32 Emulator** (`attendance-device/`) — Simulates 5 classroom fingerprint scanner units. Publishes encrypted attendance scans to MQTT broker every 10-20 seconds.

2. **Gateway Service** (`gateway/`) — Bridges MQTT (from devices) to cloud backend. Manages offline queuing, deduplication, and fingerprint template synchronization.

3. **Backend API** (`web-app/backend/`) — FastAPI application with JWT authentication, role-based access control (Admin/Faculty/Student), WebSocket real-time updates, and comprehensive REST endpoints.

4. **Frontend UI** (`web-app/frontend/`) — React application with three role-specific dashboards, live attendance feeds, enrollment management, and analytics.

## Prerequisites

- Docker & Docker Compose
- Linux/macOS/WSL2 (tested on Linux)

## Quick Start

1. **Clone the repository**
   ```bash
   cd /home/xenon/Documents/GitHub/ASE
   ```

2. **Build and start all services**
   ```bash
   docker-compose up --build
   ```

   First startup initializes PostgreSQL with schema and seed data (~5-10 seconds). Subsequent starts are faster.

3. **Access the application**
   - Frontend: `http://localhost:3000`
   - Backend API Docs: `http://localhost:8000/docs` (Swagger)
   - PostgreSQL: `localhost:5432`
   - MQTT Broker: `localhost:1883`

## Default Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Faculty | `faculty1` or `faculty2` | `pass123` |
| Student | `student01` - `student10` | `pass123` |

## Dashboards

### Admin Dashboard
- **Overview**: Real-time attendance feed (WebSocket), system stats (total students, enrolled, active devices)
- **Fingerprint Enrollment**: 
  - Enroll students with simulated fingerprint capture
  - **Revoke enrollment** for enrolled students
  - View sync status per device
- **Student Management**: Add/edit/delete students, set attendance threshold
- **Device Management**: List all ESP32 devices, battery status, firmware version, last seen
- **Past Attendance Management**:
  - **Edit attendance records** (status, timestamp, verification method)
  - **Delete attendance records** with confirmation
  - **Add manual attendance** for missed scans
  - Filter by date range and student name
- **Reports & Analytics**: Attendance % by course, at-risk students (<75%), export CSV
- **Audit Log**: Track all user actions (paginated with filters)

### Faculty Dashboard
- **Live Attendance**: Real-time feed filtered to own courses, mark manual attendance
- **Course Reports**: Per-student attendance % by course, export CSV
- **At-Risk Students**: List students below 75% threshold with auto-email alerts

### Student Dashboard
- **Welcome**: Enrollment status, alerts if below 75% attendance
- **Attendance Summary**: Doughnut chart + per-course breakdowns
- **Attendance History**: Line chart over time, detailed table per course
- **Upcoming Schedule**: Next 7 days of classes with times and locations

## 🚀 Features

- **Real-Time Attendance**: MQTT-based device-to-gateway-to-backend pipeline (sub-3 second latency)
- **Encrypted Communication**: AES-256-GCM for biometric template data
- **Role-Based Access Control**: Admin, Faculty, Student roles with granular permissions
- **WebSocket Live Feeds**: Instant attendance updates across all connected clients
- **Template Synchronization**: Automatic fingerprint template distribution to devices
- **Enrollment Management**: 
  - Enroll students with fingerprint templates
  - Revoke enrollment and deactivate templates
  - Track sync status across all devices
- **Attendance Record Management** (Admin only):
  - Edit existing attendance records (status, timestamp, method)
  - Delete incorrect or duplicate records
  - Manually add attendance for missed scans
  - Filter and search attendance history
- **Offline Queue**: Gateway queues attendance scans when cloud backend is unavailable
- **Audit Logging**: All state-changing operations logged with user, action, IP address
- **Rate Limiting**: 100 requests/minute on authentication endpoints
- **Database Partitioning**: Attendance records partitioned monthly for performance at scale
- **Property-Based Testing**: Comprehensive test suite with bug condition and preservation tests

## System Requirements

### Seed Data Included
- 1 Admin user
- 2 Faculty users (managing 3 courses total)
- 10 Student users (8 with enrolled fingerprints)
- 3 Classrooms with assigned ESP32 devices
- 3 Courses with realistic class schedules (Mon-Fri, 3x/week)
- 50 attendance records (realistically distributed across last 30 days, weekdays only, during class hours)

All passwords are bcrypt-hashed (not plaintext).

## 📡 API Endpoints (Reference)

### Authentication
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/login` | User login, returns JWT | No |
| POST | `/api/auth/logout` | Logout, blacklist JWT | Yes |
| GET | `/api/auth/me` | Current user info | Yes |

### Students
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/students` | List all students | Admin |
| POST | `/api/students` | Add new student | Admin |
| GET | `/api/students/enrolled` | List enrolled students | Device Token |

### Enrollment Management
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/enrollment/enroll` | Enroll fingerprint | Admin |
| DELETE | `/api/enrollment/revoke/{student_id}` | **Revoke enrollment** | Admin |
| GET | `/api/enrollment/status/{student_id}` | Get enrollment status | Any |

### Attendance Management
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/attendance/live` | Last 24h attendance | Any |
| GET | `/api/attendance/history` | Past attendance with filters | Admin/Faculty |
| POST | `/api/attendance` | Record attendance (batch) | Gateway Token |
| POST | `/api/attendance/manual` | **Manually add attendance** | Admin/Faculty |
| PUT | `/api/attendance/{record_id}` | **Update attendance record** | Admin |
| DELETE | `/api/attendance/{record_id}` | **Delete attendance record** | Admin |

### Reports
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/reports/student/{student_id}` | Per-student report | Any |
| GET | `/api/reports/course/{course_id}` | Course report | Faculty/Admin |
| GET | `/api/attendance/stats` | System statistics | Admin |

### WebSocket
| Protocol | Endpoint | Description | Auth Required |
|----------|----------|-------------|---------------|
| WS | `/ws/attendance?token={jwt}` | Real-time attendance feed | Yes |

**New Endpoints** (Added in latest update):
- ✨ `DELETE /api/enrollment/revoke/{student_id}` - Revoke student enrollment
- ✨ `PUT /api/attendance/{record_id}` - Edit attendance records
- ✨ `DELETE /api/attendance/{record_id}` - Delete attendance records
- ✨ `POST /api/attendance/manual` - Add manual attendance entries

## 🧪 Testing

The project includes comprehensive property-based tests for critical functionality:

### Bug Condition Tests
Located in `web-app/backend/test_enrollment_bugfix.py`:
- Tests for enrollment endpoint 500 error fixes
- Device slot auto-assignment validation
- Database connection cleanup verification
- HTTP status code correctness (400/404/409 instead of 500)

### Preservation Tests
Located in `web-app/backend/test_enrollment_preservation.py`:
- Ensures first-time enrollment behavior is preserved
- Validates AES-256-GCM encryption
- Confirms audit logging functionality
- Verifies student enrollment status updates

### Running Tests
```bash
# Run all tests
cd web-app/backend
./run_bugfix_test.sh

# Run specific test file
python -m pytest test_enrollment_bugfix.py -v
python -m pytest test_enrollment_preservation.py -v
```

See `web-app/backend/TEST_README.md` for detailed testing documentation.

## 🔧 Troubleshooting

### PostgreSQL initialization fails
```bash
docker-compose logs postgres
```
Check for SQL syntax errors in `database/init.sql`.

### Gateway not connecting to backend
```bash
docker-compose logs gateway
```
Ensure `BACKEND_URL=http://backend:8000` in `.env` and backend is healthy.

### Frontend can't reach API
Check Vite proxy config in `web-app/frontend/vite.config.js`. In dev mode, `/api` routes should proxy to `http://localhost:8000`.

### WebSocket connection fails
Inspect browser DevTools Network tab. Verify JWT token is passed as query param: `/ws/attendance?token={token}`.

### Admin can't revoke enrollment
Ensure you're logged in as admin and the backend container has been rebuilt with the latest changes:
```bash
sudo docker compose up -d --build backend
```

### Attendance records can't be edited/deleted
Verify the backend has the latest endpoints:
```bash
curl http://localhost:8000/openapi.json | grep attendance
```
Should show `/api/attendance/{record_id}` endpoints.

## 🛑 Stopping the System

```bash
docker-compose down
```

To also remove database data:
```bash
docker-compose down -v
```

## 💻 Development Notes

- **Device Simulator**: Publishes random student scans every 10-20 seconds
- **Gateway**: Forwards records to backend every 2 seconds (with exponential backoff on failure)
- **Database**: Partitioned by month for efficient attendance record queries
- **Frontend**: Uses Material-UI components for responsive design, Zustand for state management
- **Backend**: FastAPI with uvicorn auto-reload for development
- **Testing**: Property-based testing with Hypothesis for robust validation

## 🔐 Security Notes

- Change `JWT_SECRET` and `AES_KEY` in `.env` for production
- Enable MQTT authentication (currently anonymous)
- Implement rate limiting beyond 100 req/min
- Use HTTPS in production (reverse proxy with SSL)
- Implement JWT refresh token mechanism for long-lived sessions

## ⚠️ Known Limitations

- Device sensors are simulated (no real biometric hardware)
- Email alerts for at-risk students are UI only (no actual email sending)
- MQTT broker allows anonymous connections
- No multi-factor authentication
- Single-instance deployment (no clustering)
- Attendance record edits are not versioned (no edit history)

## 🚀 Future Enhancements

- Implement real fingerprint sensor integration (ZKTeco, Suprema, etc.)
- Add JWT refresh token flow for session extension
- Implement parent/guardian notification system
- Add geolocation verification for attendance
- Support for mobile native app (React Native)
- Multi-campus deployment with federated identity
- Attendance record version history and audit trail
- Bulk attendance import/export functionality
- Advanced analytics with ML-based anomaly detection

## 📝 Recent Updates

### Version 1.1.0 (April 2026)
- ✅ Fixed enrollment endpoint 500 error (device_slot constraint violation)
- ✅ Added enrollment revoke functionality for admins
- ✅ Implemented attendance record editing (status, timestamp, method)
- ✅ Added attendance record deletion with confirmation
- ✅ Added manual attendance entry for admins/faculty
- ✅ Improved error handling with specific HTTP status codes (400/404/409)
- ✅ Added database connection cleanup in finally blocks
- ✅ Comprehensive property-based testing suite
- ✅ Updated UI with edit/delete buttons in Past Attendance tab
- ✅ Enhanced enrollment dialog with revoke confirmation

## 📄 License

This project is for educational purposes. See LICENSE file for details.

---

**Last Updated**: April 11, 2026  
**Status**: Active Development  
**Version**: 1.1.0
