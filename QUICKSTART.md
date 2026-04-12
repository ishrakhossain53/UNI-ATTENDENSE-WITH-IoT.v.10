# 🚀 Quick Start Guide

Get the University Attendance Tracking System up and running in 5 minutes!

## ⚡ Quick Command Reference

```bash
# Start project (first time)
sudo docker compose up -d --build

# Stop project (keeps data)
sudo docker compose down

# Start project (after stopping)
sudo docker compose up -d

# Restart project
sudo docker compose restart

# Fresh start (removes all data)
sudo docker compose down -v && sudo docker compose up -d --build
```

---

## Prerequisites

- Docker & Docker Compose installed
- 8GB RAM minimum
- 10GB free disk space

## Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ASE.git
cd ASE
```

## Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# (Optional) Edit .env if you need custom ports or credentials
nano .env
```

## Step 3: Start All Services

```bash
# Build and start all containers
sudo docker compose up -d --build

# This will take 2-3 minutes on first run
# Subsequent starts are much faster
```

## Step 4: Verify Services

```bash
# Check all services are running
sudo docker compose ps

# You should see 7 services running:
# - attendance_backend (healthy)
# - attendance_frontend
# - attendance_postgres (healthy)
# - attendance_redis (healthy)
# - attendance_mosquitto (healthy)
# - attendance_gateway
# - attendance_device
```

## Step 5: Access the Application

Open your browser and navigate to:

**Frontend**: http://localhost:3000

**Login Credentials**:
- **Admin**: `admin` / `admin123`
- **Faculty**: `faculty1` / `pass123`
- **Student**: `student01` / `pass123`

**API Documentation**: http://localhost:8000/docs

## 🎯 What to Try First

### As Admin

1. **View Live Attendance**
   - Go to "Overview" tab
   - Watch real-time attendance scans appear (WebSocket)

2. **Enroll a Student**
   - Go to "Fingerprint Enrollment" tab
   - Click "Enroll" on an unenrolled student
   - Click "Capture Fingerprint" (simulated)
   - Confirm enrollment

3. **Revoke Enrollment**
   - Click "Revoke" on an enrolled student
   - Confirm the action

4. **Manage Attendance Records**
   - Go to "Past Attendance" tab
   - Click "Search" to load records
   - Try editing a record (change status, timestamp)
   - Try deleting a record

5. **View Reports**
   - Go to "Reports" tab
   - See attendance statistics by course

### As Faculty

1. **View Live Attendance**
   - See real-time attendance for your courses

2. **Mark Manual Attendance**
   - Add attendance for students who missed fingerprint scan

3. **View Course Reports**
   - See per-student attendance percentages
   - Identify at-risk students (<75%)

### As Student

1. **View Your Attendance**
   - See your enrollment status
   - View attendance summary with charts
   - Check attendance history per course
   - See upcoming class schedule

## 📊 Understanding the System

### Data Flow

```
ESP32 Device (Simulated)
    ↓ MQTT (encrypted)
Gateway Service
    ↓ REST API + JWT
Backend (FastAPI)
    ↓ WebSocket
Frontend (React)
```

### What's Happening Behind the Scenes

1. **ESP32 Simulator** publishes random fingerprint scans every 10-20 seconds
2. **Gateway** receives MQTT messages and forwards to backend via REST API
3. **Backend** processes attendance, stores in PostgreSQL, broadcasts via WebSocket
4. **Frontend** receives real-time updates and displays in dashboard

## 🔧 Common Commands

### View Logs

```bash
# All services
sudo docker compose logs -f

# Specific service
sudo docker compose logs -f backend
sudo docker compose logs -f frontend
sudo docker compose logs -f gateway
```

### Restart a Service

```bash
# Restart backend
sudo docker compose restart backend

# Restart frontend
sudo docker compose restart frontend

# Restart all
sudo docker compose restart
```

### Rebuild After Code Changes

```bash
# Rebuild specific service
sudo docker compose up -d --build backend

# Rebuild all services
sudo docker compose up -d --build
```

### Stop All Services

```bash
# Stop all containers but keep data (recommended)
sudo docker compose down

# Stop and remove all data including database (fresh start)
sudo docker compose down -v
```

### Start the Project (After Stopping)

```bash
# Start all services (no rebuild needed if no code changes)
sudo docker compose up -d

# Start with rebuild (if you made code changes)
sudo docker compose up -d --build
```

### Restart the Project

```bash
# Restart all services
sudo docker compose restart

# Restart specific service
sudo docker compose restart backend
sudo docker compose restart frontend
```

### Complete Project Lifecycle Commands

```bash
# 1. FIRST TIME SETUP
sudo docker compose up -d --build

# 2. STOP PROJECT (keeps data)
sudo docker compose down

# 3. START PROJECT (after stopping)
sudo docker compose up -d

# 4. RESTART PROJECT (when running)
sudo docker compose restart

# 5. REBUILD (after code changes)
sudo docker compose up -d --build

# 6. FRESH START (removes all data)
sudo docker compose down -v
sudo docker compose up -d --build
```

### Access Database

```bash
# Connect to PostgreSQL
sudo docker compose exec postgres psql -U attendance_user -d attendance_db

# Example queries
SELECT COUNT(*) FROM students;
SELECT COUNT(*) FROM attendance_records;
SELECT * FROM students WHERE fp_enrolled = TRUE;
```

## 🐛 Troubleshooting

### Frontend Not Loading

```bash
# Check if frontend is running
sudo docker compose ps frontend

# If exited, check logs
sudo docker compose logs frontend

# Restart frontend
sudo docker compose restart frontend
```

### Backend API Not Responding

```bash
# Check backend health
curl http://localhost:8000/api/health

# Should return: {"status":"ok"}

# If not, check logs
sudo docker compose logs backend
```

### Database Connection Issues

```bash
# Check if PostgreSQL is healthy
sudo docker compose ps postgres

# Test connection
sudo docker compose exec postgres pg_isready -U attendance_user

# Should return: postgres:5432 - accepting connections
```

### WebSocket Not Connecting

1. Check browser console for errors
2. Verify JWT token is valid (login again)
3. Check backend logs for WebSocket errors
4. Ensure port 3000 is not blocked by firewall

### Port Already in Use

If you get "port already in use" errors:

```bash
# Check what's using the port
sudo lsof -i :3000  # Frontend
sudo lsof -i :8000  # Backend
sudo lsof -i :5432  # PostgreSQL

# Kill the process or change port in .env
```

## 📚 Next Steps

1. **Read the Full Documentation**
   - [README.md](README.md) - Complete system overview
   - [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
   - [CHANGELOG.md](CHANGELOG.md) - Version history

2. **Explore the Code**
   - `web-app/backend/main.py` - Backend API endpoints
   - `web-app/frontend/src/components/` - React components
   - `database/init.sql` - Database schema

3. **Run Tests**
   ```bash
   cd web-app/backend
   ./run_bugfix_test.sh
   ```

4. **Make Your First Contribution**
   - Find an issue labeled "good first issue"
   - Follow the [Contributing Guide](CONTRIBUTING.md)
   - Submit a pull request

## 🎓 Learning Resources

- **FastAPI**: https://fastapi.tiangolo.com/tutorial/
- **React**: https://react.dev/learn
- **Material-UI**: https://mui.com/material-ui/getting-started/
- **PostgreSQL**: https://www.postgresql.org/docs/current/tutorial.html
- **Docker**: https://docs.docker.com/get-started/
- **MQTT**: https://mqtt.org/getting-started/

## 💬 Getting Help

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check README.md and code comments

## ✅ Checklist

- [ ] All services running (`docker compose ps`)
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend API accessible at http://localhost:8000
- [ ] Can login as admin
- [ ] Can see live attendance updates
- [ ] Can enroll/revoke students
- [ ] Can edit/delete attendance records

If all checkboxes are checked, you're ready to go! 🎉

---

**Need Help?** Open an issue or check the [Troubleshooting](#-troubleshooting) section above.
