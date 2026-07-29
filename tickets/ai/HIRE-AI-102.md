# HIRE-AI-102 — Resume Intelligence System

**Project:** H.I.R.E. (Hiring Intelligence & Recruitment Engine)  
**Ticket ID:** HIRE-AI-102  
**Sprint:** Sprint 4 – AI Intelligence Layer  
**Status:** Draft — Pending Lead AI Engineer / CTO Approval  
**Priority:** Critical  
**Assignee:** Claude (Senior Software Engineer)  
**Reviewer:** ChatGPT (CTO)

---

# Objective

Implement the **Resume Intelligence System**, the first production AI engine built on top of the HIRE AI Orchestration Framework.

This engine is responsible for transforming an unstructured candidate resume into a structured, validated, machine-readable candidate profile that can be consumed by downstream intelligence engines.

This engine performs **information extraction only**.

It does **NOT** perform candidate scoring, ranking, recommendation, or hiring decisions.

---

# Background

Candidate resumes are submitted in inconsistent formats and layouts.

Before any AI analysis can occur, H.I.R.E. requires a standardized internal representation of every candidate.

Resume Intelligence is responsible for producing this representation.

The extracted information will later be consumed by:

- Skill Intelligence
- Experience Intelligence
- Candidate Matching Engine
- Job Intelligence
- Recommendation Engine
- Hiring Decision Engine

Resume Intelligence acts as the canonical source of candidate information.

---

# Scope

This ticket includes:

- Resume parsing
- Candidate profile construction
- Validation
- Structured extraction
- Confidence scoring
- AI Framework integration

This ticket does NOT include:

- Candidate scoring
- Resume ranking
- LLM reasoning
- Semantic matching
- Skill gap analysis
- Recommendation generation

---

# Supported Input Formats (Phase 1)

The engine shall support:

- Plain Text

The following formats are planned for future tickets:

- PDF
- DOCX
- OCR
- Image resumes

---

# Functional Requirements

## FR-1 Input

Accept raw resume text through AIContext.

Example:

```python
context.data["resume_text"]
```

---

## FR-2 Personal Information Extraction

Extract:

- Full Name
- Email Address
- Phone Number
- LinkedIn URL
- GitHub URL
- Portfolio URL
- Location (if available)

---

## FR-3 Education Extraction

Extract:

- Degree
- Institution
- Specialization
- CGPA / GPA
- Graduation Year

Support multiple education entries.

---

## FR-4 Experience Extraction

Extract:

- Company
- Position
- Employment Type (if available)
- Start Date
- End Date
- Duration (if possible)
- Responsibilities

Support multiple work experiences.

---

## FR-5 Skill Extraction

Separate skills into:

Technical Skills

Example:

- Python
- Java
- FastAPI
- SQL
- Docker

Soft Skills

Example:

- Leadership
- Communication
- Teamwork
- Critical Thinking

---

## FR-6 Project Extraction

Extract:

- Project Name
- Description
- Technologies Used

Support multiple projects.

---

## FR-7 Certification Extraction

Extract:

- Certification Name
- Organization
- Completion Date

Support multiple certifications.

---

## FR-8 Language Extraction

Extract known spoken languages.

Example:

- English
- Tamil
- Hindi

---

## FR-9 Candidate Profile Construction

Build a structured CandidateProfile object containing all extracted information.

---

## FR-10 Confidence Score

Return a normalized confidence score.

Range:

```
0.0 – 1.0
```

Confidence should represent extraction quality.

---

# AI Framework Integration

The engine shall inherit:

```python
BaseEngine
```

The execution flow shall follow:

```
AIContext

↓

Resume Intelligence

↓

CandidateProfile

↓

IntelligenceResult
```

The engine must integrate with:

- AIContext
- WorkflowState
- IntelligenceResult
- AI Registry
- AI Orchestrator

No custom execution logic may bypass the orchestration framework.

---

# Technical Requirements

## Engine Location

```
backend/app/ai/engines/resume_intelligence.py
```

---

## Data Models

Create models under:

```
backend/app/models/
```

Suggested models:

```
CandidateProfile

Education

Experience

Project

Certification
```

All models should use Pydantic.

---

## Parsing Strategy

Phase 1 shall use deterministic parsing only.

Allowed:

- Regular Expressions
- String Processing
- Pattern Matching
- Rule-Based Extraction

Not Allowed:

- GPT
- Claude
- Gemini
- Llama
- Ollama
- External AI APIs

Reason:

The first implementation establishes a deterministic baseline before introducing semantic AI in later tickets.

---

## Validation

The engine shall validate:

- Required fields
- Email format
- Phone number format (basic)
- Duplicate skills
- Empty values

Invalid data shall not crash execution.

---

## Error Handling

Raise framework exceptions when appropriate.

Examples:

- ContextValidationException
- EngineExecutionException

No raw exceptions shall escape the engine.

---

## Logging

Log:

- Parsing started
- Parsing completed
- Number of skills extracted
- Number of experiences extracted
- Validation warnings

Do not log sensitive resume contents.

---

# Output

The engine shall return:

```python
IntelligenceResult
```

Example:

```python
IntelligenceResult(
    engine="resume_intelligence",
    status=ExecutionStatus.SUCCESS,
    confidence=0.94,
    data=CandidateProfile(...)
)
```

---

# Acceptance Criteria

The implementation shall:

✓ Parse plain text resumes

✓ Extract candidate information

✓ Extract education

✓ Extract experience

✓ Extract skills

✓ Extract projects

✓ Extract certifications

✓ Build CandidateProfile

✓ Return IntelligenceResult

✓ Integrate with AI Framework

✓ Pass validation

✓ Handle missing fields gracefully

✓ Pass smoke tests

---

# Deliverables

Implementation:

```
backend/app/ai/engines/
    resume_intelligence.py
```

Models:

```
backend/app/models/
    candidate.py
```

Tests:

```
backend/tests/
    test_resume_intelligence.py
```

Documentation updates where required.

---

# Out of Scope

The following are explicitly excluded:

- Resume ranking
- Candidate recommendations
- Candidate scoring
- Semantic similarity
- Skill inference
- AI reasoning
- LLM integration
- PDF parsing
- DOCX parsing
- OCR
- Multi-language parsing

These capabilities belong to future AI tickets.

---

# Performance Requirements

The engine should process an average plain text resume in under:

```
250 ms
```

Memory usage should remain lightweight and deterministic.

---

# Security Considerations

The engine shall:

- Never execute embedded content
- Never store resume text permanently
- Never expose sensitive data in logs
- Treat all input as untrusted

---

# Future Enhancements

Future tickets may introduce:

- PDF parser
- DOCX parser
- OCR pipeline
- LinkedIn profile ingestion
- Semantic skill extraction
- AI-assisted parsing
- Resume quality scoring
- Candidate completeness analysis

This implementation must remain extensible for these future capabilities.

---

# Definition of Done

The ticket is considered complete when:

- All functional requirements are implemented.
- CandidateProfile models are complete.
- Resume parsing succeeds on representative resumes.
- AI Framework integration is complete.
- Tests pass successfully.
- Code compiles without warnings.
- Smoke testing passes.
- CTO review is approved.

---

# Notes for Implementation

- Follow all architecture documents (HIRE-AI-001, HIRE-AI-002, HIRE-AI-003).
- Use asynchronous engine execution.
- Keep the implementation modular and deterministic.
- Prioritize maintainability and extensibility over premature optimization.
- The engine should establish the foundation for all future candidate intelligence systems.