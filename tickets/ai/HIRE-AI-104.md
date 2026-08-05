# HIRE-AI-104 — Experience Intelligence Engine

**Sprint:** Sprint 4 – AI Intelligence Systems
**Status:** Ready for Implementation
**Priority:** Critical
**Assignee:** Claude (Senior Software Engineer)
**Reviewer:** ChatGPT (CTO)

---

# Objective

Implement the **Experience Intelligence Engine**, the third production AI Intelligence System built on top of the HIRE-AI-101 AI Framework.

This engine consumes the structured `CandidateProfile` produced by HIRE-AI-102 and analyzes only the candidate's work experience.

It must NOT parse resumes.

It must NOT analyze skills.

It must produce deterministic experience intelligence suitable for downstream systems such as Candidate Matching, Resume Scoring, Hiring Recommendation and Career Intelligence.

This ticket follows exactly the architectural pattern established by HIRE-AI-102 and HIRE-AI-103.

---

# IMPORTANT ARCHITECTURAL RULES

This ticket MUST NOT modify ANY existing framework files.

The following files are STRICTLY OFF LIMITS:

```
app/ai/base_engine.py
app/ai/context.py
app/ai/interfaces.py
app/ai/result.py
app/ai/registry.py
app/ai/orchestrator.py
app/ai/exceptions.py
```

Also DO NOT modify

```
app/models/candidate.py
```

This engine must consume the existing CandidateProfile exactly as produced by HIRE-AI-102.

---

# Input

```
context.data["candidate_profile"]
```

Type

```
CandidateProfile
```

Only

```
candidate_profile.experience
```

should be analyzed.

---

# Output

Create

```
ExperienceIntelligence
```

which will become the canonical experience analysis used by future AI engines.

---

# Deliverables

## 1.

Create

```
backend/app/models/experience_intelligence.py
```

Create appropriate Pydantic models.

Suggested models include:

```
CareerTimeline

ExperienceMetrics

EmploymentGap

CareerProgression

StabilityAnalysis

ExperienceIntelligence
```

Use your engineering judgement where necessary.

These are pure data models only.

No AI framework imports.

---

## 2.

Create

```
backend/app/ai/experience/
```

with one module per pipeline stage.

Required modules

```
timeline_builder.py

experience_calculator.py

career_progression.py

employment_gap.py

stability_analyzer.py

seniority_analyzer.py
```

Every helper module must

• contain zero AI-framework imports

• expose pure deterministic functions

• contain no logging

• contain no orchestration logic

• perform one responsibility only

Exactly the same architectural pattern used in HIRE-AI-103.

---

## 3.

Create

```
backend/app/ai/engines/experience_intelligence.py
```

Subclass

```
BaseEngine
```

The engine is responsible ONLY for orchestration.

It must

validate context

call helper modules

assemble models

calculate confidence

return IntelligenceResult

Nothing else.

---

# Pipeline

```
CandidateProfile

        │

        ▼

Timeline Builder

        │

        ▼

Experience Calculator

        │

        ▼

Career Progression

        │

        ▼

Employment Gap Analysis

        │

        ▼

Stability Analysis

        │

        ▼

Seniority Analysis

        │

        ▼

ExperienceIntelligence
```

---

# Functional Requirements

The engine must compute

• Career timeline

• Total experience

• Number of companies

• Average tenure

• Longest tenure

• Shortest tenure

• Current employment

• Employment gaps

• Career progression

• Stability score

• Seniority level

---

# Seniority

Implement deterministic thresholds.

Example

```
0–1 years

Entry

2–4

Junior

5–8

Mid

9–14

Senior

15+

Principal
```

You may slightly adjust thresholds if justified.

---

# Stability Analysis

Produce deterministic metrics such as

average tenure

job changes

longest employment

stability score

No AI.

No fuzzy logic.

---

# Employment Gap Analysis

Detect gaps between jobs whenever dates allow.

Produce

gap duration

gap count

timeline

If dates are unavailable the engine must degrade gracefully.

---

# Career Progression

Determine

promotion

lateral move

career growth

stable

unknown

using deterministic rules only.

---

# Timeline Builder

Construct a chronological employment timeline.

Must tolerate

missing dates

present employment

single job

empty experience

---

# Confidence Calculation

Use deterministic weighted confidence.

Suggested weights

```
Timeline              20%

Experience            25%

Progression           20%

Gap Analysis          15%

Stability             10%

Seniority             10%
```

Weights must sum to 1.0.

Use the same design philosophy as HIRE-AI-102 and HIRE-AI-103.

---

# Validation

validate_context()

must verify

```
candidate_profile
```

exists

is not None

is CandidateProfile

Raise

```
ContextValidationException
```

for invalid input.

---

# Engine Execution

execute()

must

catch unexpected exceptions

raise

```
EngineExecutionException
```

never expose raw exceptions

never mutate

```
context.state
```

---

# Logging

Allowed

```
experience_count

company_count

stability_score

seniority

confidence
```

Never log

candidate name

email

phone

resume text

PII

---

# Performance

Target

```
<100 ms
```

for typical resumes.

No I/O.

No network.

No database.

No AI APIs.

---

# Testing

Create

```
backend/tests/test_experience_intelligence.py
```

Target approximately 18–20 tests.

Include

✓ complete experience

✓ empty experience

✓ one job

✓ multiple jobs

✓ promotions

✓ lateral moves

✓ employment gaps

✓ no gaps

✓ current employment

✓ seniority thresholds

✓ stability analysis

✓ missing candidate_profile

✓ None candidate_profile

✓ wrong type

✓ registry integration

✓ orchestrator integration

✓ engine never mutates context.state

✓ performance

Follow the exact testing style used in HIRE-AI-102 and HIRE-AI-103.

Do NOT introduce pytest-asyncio.

Use asyncio.run().

---

# Constraints

Deterministic implementation only.

No NLP.

No LLM.

No fuzzy matching.

No database.

No network.

No framework modifications.

---

# Required Verification

Before delivery verify

• helper modules independently

• full pipeline

• confidence calculation

• performance

• registry integration

• orchestrator integration

• all tests passing

• no framework files modified

---

# Final Deliverable

Return

1. Files created

2. Architecture

3. Design decisions

4. Verification performed

5. Performance

6. Known limitations

7. Confirmation that framework files were untouched

Do NOT stop after partial implementation.

Complete the entire ticket before delivering.