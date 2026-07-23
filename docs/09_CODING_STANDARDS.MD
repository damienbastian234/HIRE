# H.I.R.E.
# 09_CODING_STANDARDS.md

---

# Human-Interactive Intelligent Recruitment Engine

## Version

1.0.0 (Sprint 0)

---

# Purpose

This document establishes the coding standards, best practices, architectural guidelines, and development conventions for H.I.R.E.

All contributors—including human developers and AI coding assistants—must follow these standards to maintain a clean, scalable, and maintainable codebase.

---

# Engineering Principles

The H.I.R.E. codebase follows these principles:

- Readability over cleverness
- Simplicity over complexity
- Consistency over personal preference
- Modularity over duplication
- Security by default
- Testability by design
- Scalability from day one

---

# Project Structure

```
backend/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── ai/
│   ├── utils/
│   └── main.py
│
├── tests/
│
├── alembic/
│
├── requirements.txt
│
└── README.md
```

---

# Python Style Guide

The project follows **PEP 8**.

Key guidelines:

- 4 spaces for indentation
- Maximum line length: 88 characters
- UTF-8 encoding
- Meaningful variable names
- Explicit imports
- Avoid wildcard imports

---

# Naming Conventions

## Variables

Use snake_case

```python
career_score
resume_id
user_profile
```

---

## Functions

Use verbs.

Examples:

```python
create_user()

extract_skills()

generate_report()

evaluate_interview()
```

---

## Classes

Use PascalCase.

```python
ResumeService

InterviewEngine

CareerAnalyzer
```

---

## Constants

Use UPPER_CASE.

```python
MAX_FILE_SIZE

SUPPORTED_FORMATS

DEFAULT_TIMEOUT
```

---

# File Naming

All filenames use snake_case.

Examples:

```
resume_service.py

career_engine.py

interview_router.py
```

---

# API Design Standards

Every endpoint must:

- Use REST conventions
- Return JSON
- Validate inputs
- Return proper HTTP status codes
- Never expose internal errors

Example:

```
POST /resume/upload

GET /profile

PUT /profile

DELETE /resume/{id}
```

---

# Error Handling

Never suppress exceptions.

Always:

- Log errors
- Return user-friendly messages
- Preserve stack traces in logs

Example:

```python
try:
    ...
except Exception as e:
    logger.exception(e)
    raise HTTPException(...)
```

---

# Logging Standards

Every important operation should log:

- Timestamp
- User ID (if available)
- Endpoint
- Processing time
- Error details

Use Python's built-in `logging` module.

---

# Database Standards

- SQLAlchemy ORM only
- No raw SQL unless justified
- UUID primary keys
- Foreign key constraints
- Use Alembic for migrations
- Never modify production schema manually

---

# AI Development Standards

Each AI engine must:

- Have a single responsibility
- Accept structured inputs
- Return structured JSON
- Validate outputs
- Log processing time
- Include confidence scores
- Handle provider failures gracefully

---

# Security Standards

Always:

- Hash passwords using bcrypt
- Validate all user input
- Sanitize uploaded files
- Protect secrets with environment variables
- Never commit API keys
- Use HTTPS in production

---

# Documentation Standards

Every module should include:

- Purpose
- Inputs
- Outputs
- Dependencies

Public functions should use docstrings.

Example:

```python
def extract_skills(text: str) -> list:
    """
    Extract technical skills from resume text.

    Args:
        text: Parsed resume content.

    Returns:
        List of extracted skills.
    """
```

---

# Git Workflow

Main branch:

```
main
```

Development branch:

```
develop
```

Feature branches:

```
feature/authentication

feature/resume-upload

feature/interview-engine
```

Bug fixes:

```
bugfix/login-error
```

---

# Commit Message Convention

Format:

```
type: short description
```

Examples:

```
feat: add resume upload endpoint

fix: resolve JWT validation issue

docs: update AI architecture

refactor: simplify interview service

test: add authentication tests
```

---

# Code Review Checklist

Before merging code:

- Code follows PEP 8
- No hardcoded secrets
- Tests pass
- Documentation updated
- Error handling implemented
- Logging added where appropriate
- No duplicated logic

---

# Testing Standards

Every feature should include:

- Unit tests
- API tests
- Edge case validation
- Error handling tests

Future additions:

- Integration tests
- Load tests
- Security tests

---

# Performance Guidelines

Aim for:

- FastAPI endpoints < 500 ms (excluding AI calls)
- Database queries optimized
- Avoid unnecessary loops
- Cache expensive operations where appropriate

---

# AI Coding Assistant Guidelines

When using Claude or ChatGPT:

- Follow existing architecture
- Do not introduce new frameworks without approval
- Keep changes focused
- Maintain backward compatibility
- Update documentation if behavior changes
- Prefer small, reviewable commits

---

# Definition of Clean Code

Clean code should be:

- Readable
- Modular
- Reusable
- Testable
- Well documented
- Secure
- Maintainable

---

# Summary

These coding standards ensure that H.I.R.E. remains consistent, scalable, and easy to maintain as the project grows. Every contributor is expected to follow these conventions to deliver production-quality software.