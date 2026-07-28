# HIRE-BE-003 — Centralized Logging System

**Sprint:** Sprint 1 – Backend Foundation
**Status:** Ready for Development
**Priority:** High
**Assignee:** Claude (Senior Backend Engineer)
**Reviewer:** ChatGPT (CTO / Software Architect)

---

# Objective

Implement a centralized, production-ready logging system for the H.I.R.E. backend.

The logging system will serve as the single logging interface for the entire application, ensuring consistent log formatting, environment-aware log levels, reusable logger instances, and automatic file generation.

This logging system will be used by all future backend components including:

- API Routes
- Authentication
- Database Layer
- AI Engine
- File Upload Engine
- Recommendation Engine
- Report Generation
- Background Tasks

This ticket only implements the logging infrastructure—not business-specific logging.

---

# Current Architecture

The backend currently contains:

backend/
│
├── app/
│   ├── api/
│   ├── core/
│   │   ├── config.py          ✅ Complete
│   │   ├── constants.py
│   │   ├── logging.py         ← IMPLEMENT HERE
│   │   └── security.py
│   │
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── main.py
│
├── requirements.txt
└── .env

Configuration management (HIRE-BE-002) is complete.

Use the existing Settings object from:

app.core.config

Do NOT introduce any additional configuration management.

---

# Scope

Implement a centralized logging system using Python's built-in logging module.

The system must support:

- Console logging
- File logging
- Multiple log levels
- Custom formatting
- Environment-aware logging
- Reusable logger creation
- Automatic log directory creation

---

# Functional Requirements

## 1. Logger Configuration

Create a reusable logging configuration inside:

app/core/logging.py

The configuration should initialize logging only once.

Avoid duplicate handlers.

---

## 2. Log Levels

Support the following standard log levels:

- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

The active logging level must depend on:

settings.DEBUG

Example:

DEBUG=True

↓

logging.DEBUG

Otherwise

↓

logging.INFO

---

## 3. Console Logging

Logs should be displayed in the terminal using a readable format.

Example:

2026-07-24 10:45:11 | INFO | app.main | H.I.R.E Backend Started

---

## 4. File Logging

Automatically create:

logs/

if it does not already exist.

Create:

logs/hire.log

Every log written to the console must also be written to this file.

---

## 5. Log Formatting

Use a consistent formatter including:

- Timestamp
- Log Level
- Module Name
- Log Message

Example:

2026-07-24 10:45:11 | INFO | app.main | Server Started

---

## 6. Logger Factory

Provide a reusable helper.

Example usage:

logger = get_logger(__name__)

Every module in the backend should use this helper rather than creating its own logger.

---

## 7. Startup Logging

Modify main.py to log application startup.

Example:

INFO
Starting H.I.R.E Backend...

Once FastAPI is ready:

INFO
H.I.R.E Backend Ready

Do not log excessively during startup.

---

## 8. Exception Logging

Support:

logger.exception(...)

with full traceback information.

No custom exception middleware is required in this ticket.

---

## 9. Thread Safety

The implementation should remain compatible with FastAPI's asynchronous execution model.

Do not implement custom async loggers.

Use Python's standard logging implementation.

---

# Non-Functional Requirements

The implementation must:

✔ Follow PEP-8

✔ Include type hints

✔ Include meaningful docstrings

✔ Avoid duplicated handlers

✔ Be production-ready

✔ Be modular

✔ Avoid global mutable state

✔ Remain lightweight

---

# Files Expected To Change

Primary:

app/core/logging.py

Secondary:

app/main.py

No other files should require modification unless absolutely necessary.

Do NOT modify:

database/

services/

utils/

models/

schemas/

security.py

constants.py

config.py (unless a tiny adjustment is absolutely required)

---

# Deliverables

Claude should provide:

1. Updated logging.py

2. Updated main.py

3. Explanation of architecture

4. Summary of implementation decisions

5. Any assumptions made

---

# Acceptance Criteria

The ticket is complete when:

✅ Logging initializes successfully

✅ Console logging works

✅ logs/hire.log is created automatically

✅ Log formatting is consistent

✅ DEBUG mode follows settings.DEBUG

✅ INFO mode is used in production

✅ Logger helper works throughout the application

✅ Startup logs appear correctly

✅ No duplicate log entries occur

✅ No runtime warnings or errors

---

# Constraints

Architecture ownership belongs to ChatGPT (CTO).

Implementation ownership belongs to Claude.

Claude may improve implementation quality but must not redesign the architecture.

Do not introduce additional frameworks or third-party logging libraries.

Use only Python's standard logging package.

---

# Testing Expectations

Verify:

- Application starts successfully.
- Log file is automatically created.
- Console logs appear correctly.
- DEBUG=True enables debug logging.
- DEBUG=False suppresses debug logging.
- Multiple imports do not duplicate handlers.
- Logger factory returns reusable logger instances.

---

# Out of Scope

Do NOT implement:

- Exception middleware
- Request logging middleware
- API analytics
- Structured JSON logging
- External logging services
- Cloud logging integrations
- Database logging
- AI logging
- Log rotation

Those will be implemented in future tickets.

---

# Completion Notes

Once implementation is complete, provide:

1. Summary of modified files

2. Explanation of design decisions

3. Verification performed

4. Any recommendations for future logging improvements

Do not implement future tickets as part of this task.