# HIRE-AI-103 — Skill Intelligence Engine

**Sprint:** Sprint 4 – Candidate Intelligence Pipeline
**Status:** Approved — Ready for Implementation
**Priority:** Critical
**Assignee:** Claude (Senior Software Engineer)
**Reviewer:** ChatGPT (CTO)

---

## Objective

Implement the **Skill Intelligence Engine**, the second production Intelligence System built on the HIRE-AI-101 framework.

This engine consumes the structured `CandidateProfile` produced by **HIRE-AI-102** and generates comprehensive skill intelligence for downstream systems such as Candidate Matching, Resume Scoring, and Job Recommendation.

This engine **must not parse resumes**. Resume parsing is exclusively the responsibility of HIRE-AI-102.

---

## Framework Rules (Must Follow)

The following framework files are **strictly off limits**:

- app/ai/base_engine.py
- app/ai/context.py
- app/ai/interfaces.py
- app/ai/result.py
- app/ai/registry.py
- app/ai/orchestrator.py
- app/ai/exceptions.py

Do **not** modify any existing framework contracts.

Do **not** modify HIRE-AI-102.

The engine must consume `CandidateProfile` exactly as implemented.

---

## Input

The engine receives:

context.data["candidate_profile"]

Type:

CandidateProfile

Validation rules:

- Missing key → ContextValidationException
- None → ContextValidationException
- Wrong type → ContextValidationException

Validation must occur inside `validate_context()`.

---

## Output

Return a standard IntelligenceResult:

engine_name="skill_intelligence"

status=ExecutionStatus.SUCCESS

confidence=float

output=SkillIntelligence.model_dump()

warnings=[]

The engine must never modify:

- context.state
- AIContext
- WorkflowState

Workflow ownership remains exclusively with AIOrchestrator.

---

## Files To Create

backend/app/models/skill_intelligence.py

backend/app/ai/engines/skill_intelligence.py

backend/tests/test_skill_intelligence.py

Create any helper modules only if they represent a clearly isolated responsibility.

---

## Architecture

The engine should orchestrate specialized components rather than embedding large amounts of processing logic.

If any processing responsibility becomes large enough (normalization, categorization, etc.), prefer extracting it into dedicated helper modules rather than expanding the engine.

The engine should primarily coordinate:

CandidateProfile
        │
        ▼
Normalization
        ▼
Categorization
        ▼
Metrics
        ▼
Gap Analysis
        ▼
SkillIntelligence
        ▼
IntelligenceResult

---

## Models

Create:

SkillCategory

Fields:

- name
- skills
- confidence

SkillMetrics

Fields:

- technical_skill_count
- soft_skill_count
- total_skills
- categorized_skills
- uncategorized_skills

SkillGap

Fields:

- missing_categories
- recommendations

SkillIntelligence

Fields:

- categories
- metrics
- gaps
- normalized_skills
- duplicate_skills

---

## Intelligence Logic

### 1. Normalize Skills

Normalize deterministic aliases only.

Example:

JS
Javascript
Java Script

↓

JavaScript

Likewise:

Python3
Py
Python

↓

Python

No AI.

No fuzzy matching.

Use deterministic lookup dictionaries.

---

### 2. Detect Duplicates

Return duplicates separately.

Example:

Python
python
Python3

↓

Normalized:

Python

Duplicates:

python
Python3

---

### 3. Categorize Skills

Example categories:

Programming Languages

Python
Java
JavaScript
Go
Rust
C++

Frameworks

FastAPI
Flask
Django
Spring
React

Databases

MySQL
PostgreSQL
MongoDB
SQLite
Redis

Cloud & DevOps

AWS
Azure
GCP
Docker
Kubernetes

Tools

Git
GitHub
Linux
Postman
Jira

Soft Skills

Leadership
Communication
Problem Solving
Teamwork
Critical Thinking

Unknown skills remain uncategorized.

---

### 4. Compute Metrics

Calculate:

- technical skill count
- soft skill count
- total skills
- category count
- uncategorized count

---

### 5. Gap Analysis

If an expected category contains zero skills:

Example:

No database skills

↓

Recommendation:

"Consider adding database experience."

Recommendations should remain generic.

Do not make job-specific recommendations.

---

## Confidence

Deterministic weighted completeness.

Suggested weights:

Normalization ............. 20%

Categorization ............ 35%

Metrics ................... 20%

Gap Analysis .............. 15%

Duplicate Detection ....... 10%

Return confidence between:

0.0

and

1.0

---

## Logging

Allowed:

technical_skill_count

soft_skill_count

category_count

confidence

Do not log:

- resume text
- candidate name
- email
- phone
- personal information

---

## Error Handling

Use:

ContextValidationException

and

EngineExecutionException

exactly as implemented in HIRE-AI-102.

No raw exceptions should escape the engine.

---

## Testing

Create:

backend/tests/test_skill_intelligence.py

Required coverage:

- Complete candidate profile
- Empty skills
- Technical skills only
- Soft skills only
- Duplicate skills
- Synonym normalization
- Unknown skills
- Missing candidate_profile
- Invalid candidate_profile type
- Engine integration
- Engine never mutates context.state
- Performance under 100ms

Reuse the same testing style used in HIRE-AI-102.

---

## Success Criteria

- Framework untouched
- HIRE-AI-102 untouched
- Clean separation of concerns
- Deterministic execution
- All tests passing
- Performance under 100ms

---

## Important

Given the scope (models + engine + helper modules + tests), build this incrementally.

1. Build and verify the data models.
2. Build helper modules (if required) and smoke-test each independently.
3. Build the engine.
4. Run end-to-end testing.
5. Verify AI framework integration.
6. Write the complete test suite.
7. Run all tests.
8. Confirm no framework files were modified.
9. Deliver a final implementation report summarizing architecture, design decisions, verification, performance, limitations, and confirmation that framework boundaries were preserved.