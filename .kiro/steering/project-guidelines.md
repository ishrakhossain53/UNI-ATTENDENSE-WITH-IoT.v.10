---
inclusion: auto
---

# Project-Specific Guidelines

## Code Style Preferences

### Python (Backend)
- Always use type hints for function parameters and return values
- Use descriptive variable names (no single letters except for loops)
- Add docstrings to all functions and classes
- Prefer f-strings over .format() or % formatting
- Maximum line length: 100 characters
- Use async/await for database operations

### JavaScript/React (Frontend)
- Use functional components with hooks (no class components)
- Use arrow functions for event handlers
- Prefer const over let, never use var
- Use Material-UI components consistently
- Add PropTypes or TypeScript types
- Keep components under 200 lines (split if larger)

### SQL (Database)
- Always use parameterized queries (never string concatenation)
- Add comments for complex queries
- Use meaningful table and column names
- Always include indexes for foreign keys

## Security Requirements

- Never commit .env files
- Always validate user input
- Use JWT for authentication
- Encrypt sensitive data (AES-256-GCM for biometric data)
- Log all state-changing operations in audit_log table
- Use role-based access control (admin/faculty/student)

## Testing Requirements

- Write property-based tests for critical functions
- Test both success and failure cases
- Mock external dependencies (database, Redis, MQTT)
- Aim for >80% code coverage
- Run tests before committing

## Documentation Requirements

- Update README.md when adding new features
- Add inline comments for complex logic
- Update API documentation in docstrings
- Keep CHANGELOG.md up to date
- Document all environment variables in .env.example

## Git Commit Guidelines

Follow Conventional Commits format:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- refactor: Code refactoring
- test: Adding tests
- chore: Maintenance tasks

Example: `feat(enrollment): add revoke functionality for admins`

## Performance Guidelines

- Use database connection pooling
- Implement caching with Redis for frequently accessed data
- Use WebSocket for real-time updates (not polling)
- Partition large tables (attendance_records by month)
- Add indexes for frequently queried columns
- Optimize N+1 queries

## Error Handling

- Return specific HTTP status codes:
  - 400: Bad Request (invalid input)
  - 401: Unauthorized (missing/invalid token)
  - 403: Forbidden (insufficient permissions)
  - 404: Not Found (resource doesn't exist)
  - 409: Conflict (constraint violation)
  - 500: Internal Server Error (unexpected errors)
- Always log errors with context
- Use try-finally for resource cleanup
- Provide user-friendly error messages

## Deployment Checklist

Before deploying to production:
- [ ] Change all secrets in .env
- [ ] Enable MQTT authentication
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and logging
- [ ] Configure automated backups
- [ ] Test disaster recovery procedures
- [ ] Review security settings

## Project-Specific Notes

- This is an attendance tracking system with ESP32 fingerprint scanners
- Real-time updates are critical (use WebSocket)
- Biometric data must be encrypted at rest and in transit
- System must handle offline scenarios (gateway queuing)
- Database is partitioned monthly for performance
- All passwords are bcrypt-hashed
- JWT tokens expire after 1 hour (configurable)
