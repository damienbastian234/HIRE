# HIRE-AI-105 — Candidate Matching Intelligence Engine

## Objective

Implement the **Candidate Matching Intelligence Engine**, the fourth production intelligence engine built on the H.I.R.E. AI Framework.

This engine compares a structured `CandidateProfile` against a structured `JobRequirement` and produces deterministic candidate matching intelligence.

This engine **must not parse resumes**, **must not analyze skills**, and **must not calculate experience metrics**. Those responsibilities belong exclusively to:

- HIRE-AI-102 → Resume Intelligence
- HIRE-AI-103 → Skill Intelligence
- HIRE-AI-104 → Experience Intelligence

HIRE-AI-105 is purely a comparison engine.

---

# Required Architecture

```
CandidateProfile
        │
JobRequirement
        │
        ▼
CandidateMatchingEngine
        │
        ├── skill_matcher.py
        ├── experience_matcher.py
        ├── education_matcher.py
        ├── scoring.py
        ├── recommendation.py
        └── confidence.py
        │
        ▼
CandidateMatching
        │
        ▼
IntelligenceResult
```

Exactly the same orchestration pattern used by HIRE-AI-103 and HIRE-AI-104.

The engine itself should contain almost no business logic.

---

# Files to Create

## Models

```
backend/app/models/candidate_matching_model.py
```

---

## Helper modules

Create a new package:

```
backend/app/ai/matching/
```

containing:

```
skill_matcher.py
experience_matcher.py
education_matcher.py
scoring.py
recommendation.py
confidence.py
```

Each module must be completely independent.

No module may import another helper module.

---

## Engine

```
backend/app/ai/engines/candidate_matching.py
```

---

## Tests

```
backend/tests/test_candidate_matching.py
```

---

# Data Models

Create deterministic Pydantic models.

Example model names:

```
SkillMatch
ExperienceMatch
EducationMatch
OverallScore
Recommendation
CandidateMatching
```

Fields should include:

### SkillMatch

- matched_required_skills
- missing_required_skills
- matched_preferred_skills
- required_match_percentage
- preferred_match_percentage

---

### ExperienceMatch

- required_years
- candidate_years
- meets_requirement
- experience_match_percentage

---

### EducationMatch

- required_degree
- candidate_degree
- meets_requirement

---

### OverallScore

- skill_score
- experience_score
- education_score
- overall_score

---

### Recommendation

One of:

```
Strong Match
Good Match
Possible Match
Weak Match
Not Recommended
```

---

### CandidateMatching

Contains every model above plus

```
confidence
```

---

# Engine Input

Read only

```
context.data["candidate_profile"]
context.data["job_requirement"]
```

Validate both.

Raise ContextValidationException on:

- missing key
- None
- wrong type

---

# Engine Output

Return

```
IntelligenceResult
```

Exactly like previous engines.

---

# Helper Modules

## 1 Skill Matcher

Responsibilities:

Compare

Candidate skills

vs

Required skills

and

Preferred skills.

Compute

- matched required
- missing required
- matched preferred
- percentages

Case-insensitive.

Deterministic.

No fuzzy matching.

No AI.

---

## 2 Experience Matcher

Compare

Candidate total experience

(from HIRE-AI-104 output or CandidateProfile)

against

required years.

Return

percentage

and

meets requirement.

No date parsing.

---

## 3 Education Matcher

Simple deterministic equality comparison.

Example:

Bachelor

matches

Bachelor

Case-insensitive.

No NLP.

---

## 4 Scoring

Weighted score.

Default weights

```
Skills      50%
Experience  35%
Education   15%
```

Output

```
overall_score
```

between

```
0
```

and

```
100
```

---

## 5 Recommendation

Map score

```
90-100 → Strong Match

75-89 → Good Match

60-74 → Possible Match

40-59 → Weak Match

0-39 → Not Recommended
```

---

## 6 Confidence

Deterministic completeness score.

Follow same philosophy as HIRE-AI-103 and HIRE-AI-104.

Confidence measures

how complete the comparison was,

NOT

whether the candidate is good.

---

# Engine Flow

```
validate

↓

skill matcher

↓

experience matcher

↓

education matcher

↓

scoring

↓

recommendation

↓

confidence

↓

CandidateMatching

↓

IntelligenceResult
```

---

# Logging

Allowed:

```
overall_score

confidence

matched_required

missing_required

recommendation
```

Never log

candidate name

email

phone

resume

PII

---

# Constraints

Do NOT modify

```
app/ai/base_engine.py

app/ai/context.py

app/ai/result.py

app/ai/interfaces.py

app/ai/orchestrator.py

app/ai/registry.py

app/ai/exceptions.py
```

Do NOT modify

```
candidate.py
```

Do NOT modify previous engines.

---

# Performance

Entire engine

under

100ms

for normal candidate.

---

# Unit Tests

Minimum 20 tests.

Include:

✓ Complete candidate

✓ Empty candidate

✓ Missing job requirement

✓ Missing candidate

✓ Wrong type

✓ Skill match

✓ Missing skills

✓ Experience pass

✓ Experience fail

✓ Education pass

✓ Education fail

✓ Score calculation

✓ Recommendation thresholds

✓ Confidence

✓ Registry integration

✓ Orchestrator integration

✓ Context never mutated

✓ Performance

✓ Empty skills

✓ Empty requirements

---

# Verification

Run

```
pytest
```

All existing tests must continue passing.

No framework files modified.

No previous engine modified.

Return:

1. Files created

2. Architecture summary

3. Design decisions

4. Verification performed

5. Performance

6. Known limitations

7. Confirmation framework untouched

Do not skip any step.

Build incrementally:

Step 1

Models

↓

Step 2

Each helper module independently with smoke tests

↓

Step 3

Engine

↓

Step 4

Integration

↓

Step 5

Full pytest suite

↓

Step 6

Final verification