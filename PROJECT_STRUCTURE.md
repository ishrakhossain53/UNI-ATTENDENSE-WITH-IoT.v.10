# 📁 Project Structure

Complete file structure of the University Attendance Tracking System.

```
ASE/
│
├── 📄 .env                              # Environment configuration (DO NOT COMMIT)
├── 📄 .env.example                      # Environment template with documentation
├── 📄 docker-compose.yml                # Docker orchestration configuration
├── 📄 README.md                         # Main project documentation
├── 📄 QUICKSTART.md                     # Quick start guide for new users
├── 📄 CHANGELOG.md                      # Version history and changes
├── 📄 CONTRIBUTING.md                   # Contribution guidelines
├── 📄 PROJECT_STRUCTURE.md              # This file
│
├── 📁 .kiro/                            # Kiro AI specifications
│   └── 📁 specs/
│       └── 📁 enrollment-endpoint-500-error-fix/
│           ├── 📄 bugfix.md             # Bug condition documentation
│           ├── 📄 design.md             # Fix design document
│           ├── 📄 tasks.md              # Implementation task list
│           └── 📄 .config.kiro          # Spec configuration
│
├── 📁 attendance-device/                # ESP32 Device Simulator
│   ├── 📄 Dockerfile                    # Container configuration
│   ├── 📄 esp_emulator.py              # Simulates 5 ESP32 fingerprint scanners
│   ├── 📄 requirements.txt             # Python dependencies
│   └── 📁 __pycache__/                 # Python cache (ignored)
│
├── 📁 gateway/                          # MQTT-to-REST Gateway Service
│   ├── 📄 Dockerfile                    # Container configuration
│   ├── 📄 gateway_service.py           # Bridges MQTT and backend API
│   ├── 📄 requirements.txt             # Python dependencies
│   └── 📁 __pycache__/                 # Python cache (ignored)
│
├── 📁 database/                         # PostgreSQL Database
│   └── 📄 init.sql                     # Schema, seed data, partitions, indexes
│
├── 📁 mosquitto/                        # MQTT Broker Configuration
│   └── 📁 config/
│       └── 📄 mosquitto.conf           # MQTT broker settings
│
└── 📁 web-app/                          # Full-Stack Web Application
    │
    ├── 📁 backend/                      # FastAPI Backend API
    │   ├── 📄 Dockerfile                # Container configuration
    │   ├── 📄 main.py                  # Main API application (2000+ lines)
    │   │                                # - Authentication & JWT
    │   │                                # - Student management
    │   │                                # - Enrollment management (enroll/revoke)
    │   │                                # - Attendance management (CRUD)
    │   │                                # - Device management
    │   │                                # - Reports & analytics
    │   │                                # - WebSocket real-time updates
    │   │                                # - Audit logging
    │   ├── 📄 requirements.txt         # Python dependencies
    │   ├── 📄 test_enrollment_bugfix.py        # Bug condition tests
    │   ├── 📄 test_enrollment_preservation.py  # Preservation tests
    │   ├── 📄 run_bugfix_test.sh              # Test runner script
    │   ├── 📄 TEST_README.md                   # Testing documentation
    │   ├── 📄 TASK1_SUMMARY.md                 # Bugfix summary
    │   └── 📁 __pycache__/             # Python cache (ignored)
    │
    └── 📁 frontend/                     # React Frontend Application
        ├── 📄 Dockerfile                # Multi-stage build configuration
        ├── 📄 .dockerignore            # Docker ignore patterns
        ├── 📄 nginx.conf               # Nginx reverse proxy config
        ├── 📄 package.json             # Node.js dependencies
        ├── 📄 package-lock.json        # Locked dependency versions
        ├── 📄 vite.config.js           # Vite build configuration
        ├── 📄 index.html               # HTML entry point
        │
        ├── 📁 public/                   # Static assets
        │   └── 📄 index.html           # Public HTML template
        │
        ├── 📁 src/                      # React source code
        │   ├── 📄 index.jsx            # App entry point
        │   ├── 📄 App.jsx              # Main app component with routing
        │   ├── 📄 api.jsx              # Axios API client configuration
        │   ├── 📄 store.jsx            # Zustand state management
        │   │
        │   └── 📁 components/           # React components
        │       ├── 📄 Login.jsx                # Login page
        │       ├── 📄 AdminDashboard.jsx       # Admin dashboard (700+ lines)
        │       │                                # - Overview & live feed
        │       │                                # - Fingerprint enrollment/revoke
        │       │                                # - Student management
        │       │                                # - Device management
        │       │                                # - Past attendance (edit/delete)
        │       │                                # - Reports & analytics
        │       │                                # - Audit log
        │       ├── 📄 FacultyDashboard.jsx     # Faculty dashboard
        │       │                                # - Live attendance
        │       │                                # - Course reports
        │       │                                # - At-risk students
        │       └── 📄 StudentDashboard.jsx     # Student dashboard
        │                                        # - Attendance summary
        │                                        # - Attendance history
        │                                        # - Upcoming schedule
        │
        ├── 📁 dist/                     # Build output (generated)
        │   ├── 📁 public/              # Built HTML
        │   └── 📁 assets/              # Built JS/CSS
        │
        └── 📁 node_modules/             # Node.js dependencies (ignored)
```

## 🔑 Key Files Explained

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (secrets, ports, config) |
| `.env.example` | Template for .env with documentation |
| `docker-compose.yml` | Orchestrates all 7 services |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `QUICKSTART.md` | 5-minute setup guide |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | Development guidelines |
| `PROJECT_STRUCTURE.md` | This file |

### Backend Files

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | 2000+ | Complete FastAPI application |
| `test_enrollment_bugfix.py` | 200+ | Bug condition tests |
| `test_enrollment_preservation.py` | 150+ | Preservation tests |
| `run_bugfix_test.sh` | 20 | Test runner script |

### Frontend Files

| File | Lines | Purpose |
|------|-------|---------|
| `AdminDashboard.jsx` | 700+ | Admin interface with 7 tabs |
| `FacultyDashboard.jsx` | 400+ | Faculty interface |
| `StudentDashboard.jsx` | 500+ | Student interface |
| `api.jsx` | 50 | Axios HTTP client |
| `store.jsx` | 30 | Zustand state management |

### Database Files

| File | Lines | Purpose |
|------|-------|---------|
| `init.sql` | 800+ | Complete database schema, seed data, partitions |

## 📊 File Statistics

```
Total Files: ~50
Total Lines of Code: ~5,000+

Breakdown:
- Backend (Python): ~2,500 lines
- Frontend (JavaScript/React): ~2,000 lines
- Database (SQL): ~800 lines
- Configuration: ~200 lines
- Documentation: ~2,000 lines
```

## 🎯 Important Directories

### Development
- `web-app/backend/` - Backend API development
- `web-app/frontend/src/` - Frontend UI development
- `database/` - Database schema changes

### Testing
- `web-app/backend/test_*.py` - Backend tests
- `.kiro/specs/` - Specification-driven development

### Configuration
- Root directory - Docker and environment config
- `mosquitto/config/` - MQTT broker settings
- `web-app/frontend/` - Nginx and Vite config

## 🚫 Ignored Files/Directories

These are in `.gitignore` and should NOT be committed:

```
.env                    # Contains secrets
__pycache__/           # Python cache
node_modules/          # Node.js dependencies
dist/                  # Build output
*.pyc                  # Python bytecode
.DS_Store              # macOS files
```

## 📦 Docker Volumes

Persistent data stored in Docker volumes:

```
postgres_data/         # PostgreSQL database files
```

## 🔄 Build Artifacts

Generated during build/runtime:

```
web-app/frontend/dist/           # Vite build output
web-app/backend/__pycache__/     # Python cache
gateway/__pycache__/             # Python cache
attendance-device/__pycache__/   # Python cache
```

## 🌐 Network Architecture

```
Docker Network: attendance-net (bridge)
├── postgres:5432
├── redis:6379
├── mosquitto:1883
├── backend:8000
├── frontend:80 → localhost:3000
├── gateway (internal)
└── attendance-device (internal)
```

## 📝 Notes

- **Backend**: Auto-reloads on code changes (uvicorn --reload)
- **Frontend**: Requires rebuild for changes (docker compose up -d --build frontend)
- **Database**: Schema changes require container restart
- **Tests**: Run from `web-app/backend/` directory

## 🔗 Related Documentation

- [README.md](README.md) - Full system documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development workflow
- [CHANGELOG.md](CHANGELOG.md) - Version history

---

**Last Updated**: April 11, 2026  
**Version**: 1.1.0
