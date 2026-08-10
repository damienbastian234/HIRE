# HIRE-BE-006 — Job Requirement Domain Model

## Objective

Implement the canonical **Job Requirement** domain model for H.I.R.E.

This ticket creates the official model that every future backend service and AI engine will consume.

This model represents a structured job posting.

It is the equivalent of `CandidateProfile`, but for employers.

This ticket creates **models only**.

Do NOT create:

- Database tables
- SQLAlchemy models
- FastAPI endpoints
- CRUD services
- AI engines
- Business logic

---

# Existing Context

Already completed:

- HIRE-AI-101 — AI Framework
- HIRE-AI-102 — Resume Intelligence
- HIRE-AI-103 — Skill Intelligence
- HIRE-AI-104 — Experience Intelligence

Current canonical candidate model:

```
backend/app/models/candidate.py
```

This ticket creates the canonical job model.

Future engines (HIRE-AI-105+) will compare:

```
CandidateProfile
```

against

```
JobRequirement
```

---

# Files

Create only

```
backend/app/models/job_requirement.py
```

Create

```
backend/tests/test_job_requirement_model.py
```

No additional files unless absolutely necessary.

---

# Required Models

## EmploymentType

Enum

```
FULL_TIME
PART_TIME
CONTRACT
INTERN
FREELANCE
TEMPORARY
```

---

## WorkMode

Enum

```
ONSITE
REMOTE
HYBRID
```

---

## ExperienceRequirement

Fields

```
minimum_years: float

preferred_years: float | None
```

Validation

- minimum >= 0
- preferred >= minimum

---

## SalaryRange

Fields

```
minimum: float | None

maximum: float | None

currency: str = "INR"
```

Validation

maximum >= minimum

---

## EducationRequirement

Fields

```
degrees: list[str]

fields_of_study: list[str]

minimum_percentage: float | None

minimum_cgpa: float | None
```

Validation

CGPA

```
0-10
```

Percentage

```
0-100
```

---

## SkillRequirement

Fields

```
name

required

minimum_proficiency

minimum_years
```

Validation

minimum_years >=0

No fuzzy matching.

No normalization.

---

## JobRequirement

Fields

```
job_id

title

department

company

location

work_mode

employment_type

description

responsibilities

required_skills

preferred_skills

experience

education

salary

keywords

created_at

updated_at
```

Responsibilities

```
list[str]
```

Required Skills

```
list[SkillRequirement]
```

Preferred Skills

```
list[SkillRequirement]
```

Keywords

```
list[str]
```

---

# Validation Rules

Reject

```
negative years
```

Reject

```
CGPA >10
```

Reject

```
CGPA <0
```

Reject

```
percentage >100
```

Reject

```
salary min > salary max
```

Trim whitespace.

Convert empty strings to None where appropriate.

Do NOT infer values.

---

# Constraints

Do NOT modify

```
candidate.py
```

Do NOT modify

```
app/ai/*
```

Do NOT import

- SQLAlchemy
- FastAPI
- AI framework
- Database

Pure Pydantic models only.

---

# Documentation

Document every

- model
- field
- validator

Documentation quality must match

```
candidate.py
```

---

# Tests

Create

```
backend/tests/test_job_requirement_model.py
```

Minimum 25 tests.

Include

### Enums

- EmploymentType
- WorkMode

### Experience

- valid
- invalid
- preferred < minimum

### Salary

- valid
- invalid
- default currency

### Education

- valid CGPA
- invalid CGPA
- valid percentage
- invalid percentage

### Skills

- required
- optional
- invalid years

### JobRequirement

- minimal object
- full object
- empty responsibilities
- empty preferred skills
- empty keywords

### Serialization

- model_dump()
- model_validate()
- JSON serialization

### Performance

Construct 1000 JobRequirement objects.

Execution under

```
100 ms
```

---

# Verification

Run

```
pytest
```

All previous tests must continue passing.

No existing tests may fail.

---

# Deliverables

Provide

1. Files created
2. Architecture explanation
3. Validation strategy
4. Tests written
5. Performance verification
6. Known limitations
7. Confirmation that no existing framework files were modified

---

# Implementation Process

Build incrementally.

Step 1

Models

↓

Step 2

Validators

↓

Step 3

Unit tests

↓

Step 4

Performance verification

↓

Step 5

Run full pytest suite

↓

Step 6

Final verification

Do not skip any step.