---
inclusion: auto
---

# My Personal Preferences

## Communication Style

- Be concise and direct
- Use bullet points for lists
- Provide code examples when explaining concepts
- Explain your reasoning when making recommendations
- Ask clarifying questions if requirements are unclear

## Code Generation Preferences

- Always show the complete file when making changes (not just snippets)
- Add comments explaining complex logic
- Use meaningful variable names
- Follow the project's existing code style
- Test code before suggesting it

## Problem-Solving Approach

1. Understand the problem fully before coding
2. Consider edge cases and error scenarios
3. Think about performance implications
4. Consider security implications
5. Provide multiple solutions when appropriate

## Documentation Preferences

- Keep documentation up-to-date with code changes
- Use clear, simple language
- Include examples for complex features
- Add diagrams for architecture explanations
- Keep README.md as the main entry point

## Testing Preferences

- Write tests for new features
- Use property-based testing for critical functions
- Test both happy path and error cases
- Mock external dependencies
- Provide test data examples

## Workflow Preferences

- Commit frequently with clear messages
- Create feature branches for new work
- Review changes before pushing
- Keep pull requests focused and small
- Update documentation with code changes

## Tools and Technologies

**Preferred Stack**:
- Backend: Python with FastAPI
- Frontend: React with Material-UI
- Database: PostgreSQL
- Caching: Redis
- Messaging: MQTT
- Containerization: Docker Compose

**Preferred Libraries**:
- Testing: pytest, Hypothesis
- HTTP Client: Axios
- State Management: Zustand
- Charts: Chart.js
- Authentication: JWT

## Custom Instructions

- Always check if services are running before making changes
- Verify .env file exists and has correct values
- Test endpoints after making backend changes
- Rebuild frontend container after UI changes
- Check logs when debugging issues
- Use `sudo docker compose` commands (not `docker-compose`)

## Things to Avoid

- Don't use class components in React (use functional components)
- Don't use string concatenation for SQL queries (use parameterized queries)
- Don't commit sensitive data (.env, secrets, credentials)
- Don't make breaking changes without updating documentation
- Don't skip error handling
- Don't use synchronous operations for I/O (use async/await)

## Helpful Reminders

- Backend auto-reloads on code changes (uvicorn --reload)
- Frontend requires rebuild: `sudo docker compose up -d --build frontend`
- Database changes require container restart
- Port 5432 may conflict with system PostgreSQL (stop it first)
- Always verify .gitignore before committing
- Check GitHub repository after pushing changes
