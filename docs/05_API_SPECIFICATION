# H.I.R.E.
# 05_API_SPECIFICATION.md

---

# Human-Interactive Intelligent Recruitment Engine

## Version

1.0.0 (Sprint 0)

---

# Purpose

This document defines the REST API specification for H.I.R.E.

It describes the API structure, authentication strategy, endpoint conventions, request and response formats, status codes, and versioning strategy.

The API serves as the communication layer between the frontend, backend, AI services, and future integrations.

---

# API Design Principles

The H.I.R.E. API follows the following principles:

- RESTful Architecture
- JSON Request & Response Format
- Stateless Communication
- JWT Authentication
- Versioned APIs
- Standard HTTP Status Codes
- Consistent Response Structure
- Clear Error Messages

---

# Base URL

```
http://localhost:8000/api/v1
```

Production:

```
https://api.hire.ai/api/v1
```

---

# Authentication

Authentication is handled using JSON Web Tokens (JWT).

Protected endpoints require:

```
Authorization: Bearer <JWT_TOKEN>
```

---

# Standard Success Response

```json
{
    "success": true,
    "message": "Request completed successfully.",
    "data": {}
}
```

---

# Standard Error Response

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": []
}
```

---

# HTTP Status Codes

| Code | Meaning |
|-------|----------|
| 200 | OK |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# Authentication Module

## Register User

POST

```
/auth/register
```

Request

```json
{
    "email": "john@example.com",
    "password": "password123"
}
```

Response

```json
{
    "success": true,
    "message": "User registered successfully."
}
```

---

## Login

POST

```
/auth/login
```

Returns:

- JWT Access Token
- User Information

---

## Get Current User

GET

```
/auth/me
```

---

# Profile Module

## Get Profile

GET

```
/profile
```

---

## Update Profile

PUT

```
/profile
```

---

# Resume Module

## Upload Resume

POST

```
/resume/upload
```

Multipart Form Data

Accepted Formats

- PDF
- DOCX (Future)

Response

- Resume ID
- Upload Status

---

## Get Resume

GET

```
/resume/{resume_id}
```

---

## Delete Resume

DELETE

```
/resume/{resume_id}
```

---

# Career Intelligence Module

## Analyze Resume

POST

```
/career/analyze
```

Returns

- Career Score
- Skill Analysis
- Strengths
- Weaknesses
- Skill Gaps

---

## Get Career Report

GET

```
/career/report/{report_id}
```

---

# Recommendation Module

## Get Recommendations

GET

```
/recommendations
```

Returns

- Learning Resources
- Suggested Certifications
- Projects
- Improvement Plan

---

# AI Interview Module

## Start Interview

POST

```
/interview/start
```

Response

- Session ID
- First Question

---

## Get Next Question

POST

```
/interview/question
```

---

## Submit Answer

POST

```
/interview/answer
```

Request

```json
{
    "session_id": "...",
    "answer": "..."
}
```

Response

```json
{
    "score": 8.5,
    "feedback": "...",
    "next_question": "..."
}
```

---

## End Interview

POST

```
/interview/end
```

Returns

- Final Score
- Overall Feedback
- Interview Summary

---

# Dashboard Module

## Dashboard Overview

GET

```
/dashboard
```

Returns

- Career Score
- Resume Status
- Interview Performance
- Recommendations
- Progress

---

# Health Module

## Health Check

GET

```
/health
```

Response

```json
{
    "status": "healthy"
}
```

---

# Version Module

## API Version

GET

```
/version
```

---

# Error Handling

Every error response includes:

- success
- message
- optional errors list

Example:

```json
{
    "success": false,
    "message": "Resume not found.",
    "errors": []
}
```

---

# API Security

The API implements:

- JWT Authentication
- Password Hashing
- Request Validation
- Input Sanitization
- File Validation
- Authorization
- Rate Limiting (Future)

---

# API Versioning Strategy

Current Version

```
v1
```

Future Versions

```
v2
v3
```

Versioning ensures backward compatibility as the platform evolves.

---

# Future API Modules

Future releases may introduce:

- Recruiter APIs
- University APIs
- Company APIs
- Robot APIs
- Job Matching APIs
- Notification APIs
- Analytics APIs

---

# Summary

The H.I.R.E. REST API is designed to provide a secure, scalable, and modular communication layer between all platform components.

By following REST principles, standardized response formats, and versioned endpoints, the API ensures maintainability, extensibility, and compatibility with future platform growth.