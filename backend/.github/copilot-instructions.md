# H.I.R.E GitHub Copilot Instructions

## Project

H.I.R.E.
Hiring Intelligence Recruitment Engine

Backend Stack

- Python 3.13
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic v2

Frontend

- React
- TypeScript
- TailwindCSS

---

# Architecture

Presentation

↓

API Routers

↓

Services

↓

AI Engines

↓

Database

---

# AI Engine Rules

Every AI engine:

- inherits BaseEngine
- returns IntelligenceResult
- validates context before execution
- never touches the database
- never mutates context.state
- only orchestrates helper modules

---

# Helper Module Rules

Helper modules

- contain business logic
- never import BaseEngine
- never import AIContext
- never import AIOrchestrator
- never import EngineRegistry

They must remain completely independent.

---

# Models

Models contain

- data only
- validation
- no business logic

---

# Services

Services

- coordinate business operations
- may call AI engines
- may call repositories

---

# Routers

Routers

- validate requests
- call services
- return responses

Never place business logic inside routers.

---

# Protected Files

Never modify unless explicitly requested.

app/ai/base_engine.py

app/ai/context.py

app/ai/interfaces.py

app/ai/result.py

app/ai/orchestrator.py

app/ai/registry.py

app/ai/exceptions.py

---

# Coding Standards

- Type hints required
- Docstrings required
- Small functions
- Single Responsibility Principle
- Composition over inheritance
- No duplicated logic
- Deterministic processing
- No AI/NLP unless the ticket explicitly requires it

---

# Testing

Every ticket must include

- pytest tests
- edge cases
- empty input tests
- invalid input tests
- integration tests when appropriate

---

# Performance

Target execution

<100ms

---

# Logging

Never log

- resume text
- candidate names
- emails
- phone numbers
- addresses

Only log

- engine
- confidence
- execution time
- counts
- metrics

---

# Folder Structure

app/

ai/

engines/

experience/

skills/

parsers/

models/

services/

api/

tests/

---

Always follow the architecture already present in the repository.