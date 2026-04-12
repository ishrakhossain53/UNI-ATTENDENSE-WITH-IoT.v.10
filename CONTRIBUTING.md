# Contributing to University Attendance Tracking System

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences

## 🚀 Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/ishrakhossain53/UNI-ATTENDENSE-WITH-IoT.v.10.git
   cd ASE
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/ASE.git
   ```

## 💻 Development Setup

### Prerequisites
- Docker & Docker Compose
- Git
- Text editor (VS Code recommended)
- Basic knowledge of Python, JavaScript, and SQL

### Initial Setup

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Start all services**:
   ```bash
   docker compose up -d --build
   ```

3. **Verify services are running**:
   ```bash
   docker compose ps
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Development Mode

The backend runs with auto-reload enabled. Changes to `web-app/backend/main.py` will automatically restart the server.

For frontend changes, rebuild the container:
```bash
docker compose up -d --build frontend
```

## 📁 Project Structure

```
ASE/
├── attendance-device/    # ESP32 simulator
├── gateway/             # MQTT gateway service
├── database/            # PostgreSQL schema and seeds
├── mosquitto/           # MQTT broker config
└── web-app/
    ├── backend/         # FastAPI application
    └── frontend/        # React application
```

## 🔄 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `hotfix/` - Critical production fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation as needed

### 3. Test Your Changes

```bash
# Backend tests
cd web-app/backend
./run_bugfix_test.sh

# Manual testing
# - Test in browser
# - Check API endpoints
# - Verify WebSocket connections
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

### 5. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 6. Create Pull Request

- Go to GitHub and create a PR
- Fill out the PR template
- Link related issues
- Request review

## 🧪 Testing Guidelines

### Backend Testing

We use property-based testing with Hypothesis for robust validation.

**Test Structure**:
```python
from hypothesis import given, strategies as st

@given(st.text())
def test_property(input_data):
    # Test implementation
    assert expected_behavior(input_data)
```

**Running Tests**:
```bash
cd web-app/backend

# Run all tests
./run_bugfix_test.sh

# Run specific test file
python -m pytest test_enrollment_bugfix.py -v

# Run with coverage
python -m pytest --cov=main --cov-report=html
```

**Test Categories**:
1. **Bug Condition Tests** - Verify bugs are fixed
2. **Preservation Tests** - Ensure existing behavior is preserved
3. **Integration Tests** - Test API endpoints end-to-end

### Frontend Testing

Manual testing checklist:
- [ ] Login/logout functionality
- [ ] Role-based access control
- [ ] Real-time WebSocket updates
- [ ] Form validation
- [ ] Error handling
- [ ] Responsive design

## 📝 Coding Standards

### Python (Backend)

**Style Guide**: PEP 8

```python
# Good
def enroll_fingerprint(student_id: str, template_data: str) -> dict:
    """Enroll a student's fingerprint template.
    
    Args:
        student_id: UUID of the student
        template_data: Base64-encoded fingerprint template
        
    Returns:
        dict: Enrollment result with template_id
    """
    # Implementation
    pass

# Bad
def enroll(sid,td):
    # No docstring, unclear variable names
    pass
```

**Key Principles**:
- Use type hints
- Write docstrings for functions
- Keep functions focused and small
- Use meaningful variable names
- Handle errors explicitly

### JavaScript/React (Frontend)

**Style Guide**: Airbnb JavaScript Style Guide

```javascript
// Good
const handleEnroll = async () => {
  if (!selectedStudent) return;
  
  try {
    await api.post('/enrollment/enroll', {
      student_id: selectedStudent.student_id,
      template_data_base64: template
    });
    setSuccess('Enrollment successful');
  } catch (err) {
    setError('Enrollment failed');
  }
};

// Bad
const h = async()=>{if(!s)return;try{await api.post('/enrollment/enroll',{student_id:s.student_id,template_data_base64:t});setSuccess('Enrollment successful');}catch(e){setError('Enrollment failed');}};
```

**Key Principles**:
- Use functional components with hooks
- Keep components small and focused
- Use meaningful component and variable names
- Handle loading and error states
- Use Material-UI components consistently

### SQL (Database)

```sql
-- Good: Clear, formatted, with comments
-- Create attendance records table with monthly partitioning
CREATE TABLE attendance_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(student_id),
    classroom_id UUID NOT NULL REFERENCES classrooms(classroom_id),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'present',
    CONSTRAINT valid_status CHECK (status IN ('present', 'absent', 'manual'))
) PARTITION BY RANGE (timestamp);

-- Bad: Unclear, no formatting
CREATE TABLE attendance_records(record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),student_id UUID NOT NULL REFERENCES students(student_id),classroom_id UUID NOT NULL REFERENCES classrooms(classroom_id),timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),status VARCHAR(20) DEFAULT 'present');
```

## 📋 Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/).

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(enrollment): add revoke functionality for admins

- Added DELETE /api/enrollment/revoke/{student_id} endpoint
- Updated frontend dialog to show revoke confirmation
- Added audit logging for revoke actions

Closes #123
```

```bash
fix(attendance): resolve 500 error on second enrollment

- Auto-assign device_slot instead of hardcoding to 0
- Add database connection cleanup in finally blocks
- Return specific HTTP status codes (400/404/409)

Fixes #456
```

## 🔍 Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with main branch

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] No regressions found

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Closes #123
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests
2. **Code Review**: At least one maintainer reviews
3. **Feedback**: Address review comments
4. **Approval**: Maintainer approves PR
5. **Merge**: Maintainer merges to main branch

## 🐛 Reporting Bugs

**Before Reporting**:
- Check existing issues
- Verify it's reproducible
- Test on latest version

**Bug Report Template**:
```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Docker version: [e.g., 24.0.0]
- Browser: [e.g., Chrome 120]

**Logs**
```
Paste relevant logs here
```

**Screenshots**
Add screenshots if applicable
```

## 💡 Feature Requests

**Feature Request Template**:
```markdown
**Problem Statement**
Describe the problem this feature would solve

**Proposed Solution**
Describe your proposed solution

**Alternatives Considered**
Other solutions you've considered

**Additional Context**
Any other context or screenshots
```

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Material-UI Documentation](https://mui.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Hypothesis Testing](https://hypothesis.readthedocs.io/)

## 🙏 Thank You!

Your contributions make this project better. Thank you for taking the time to contribute!

## 📧 Contact

For questions or discussions, please open an issue or reach out to the maintainers.
