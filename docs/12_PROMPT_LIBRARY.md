# H.I.R.E.
# 12_PROMPT_LIBRARY.md

---

# Purpose

This document serves as the central repository for all prompts used throughout the H.I.R.E. platform.

Every prompt should be version-controlled, documented, and reusable.

---

# Prompt Design Principles

Every prompt follows the same structure:

1. System Role
2. Context
3. Task
4. Constraints
5. Output Format

All outputs must be valid JSON unless otherwise specified.

---

# Prompt Versioning

Example:

Resume Prompt

Version: v1.0

Owner: AI Team

Last Updated: YYYY-MM-DD

---

# Resume Intelligence Prompt

## Purpose

Extract structured information from resumes.

### System

You are an experienced technical recruiter and resume analyst.

### Task

Extract:

- Education
- Skills
- Projects
- Experience
- Certifications

Return only valid JSON.

### Expected Output

{
  "education": [],
  "skills": [],
  "projects": [],
  "experience": [],
  "certifications": []
}

---

# Skill Extraction Prompt

Purpose:

Categorize skills into:

- Programming Languages
- Frameworks
- Databases
- Tools
- Cloud
- Soft Skills

Return JSON.

---

# Career Intelligence Prompt

Purpose:

Evaluate career readiness.

Output:

- Career Score
- Strengths
- Weaknesses
- Skill Gaps
- Career Paths

---

# Recommendation Prompt

Generate:

- Learning Resources
- Certifications
- Resume Improvements
- Practice Projects

Rank recommendations by priority.

---

# Interview Question Prompt

Generate interview questions based on:

- Candidate profile
- Difficulty
- Previous answers

Return one question at a time.

---

# Interview Evaluation Prompt

Evaluate:

- Accuracy
- Communication
- Completeness
- Problem Solving

Return:

- Score
- Feedback
- Improvements

---

# Prompt Validation

Every prompt must:

- Produce deterministic JSON
- Avoid hallucinations
- Reject unsupported requests
- Remain provider-independent

---

# Prompt Lifecycle

Draft

↓

Review

↓

Testing

↓

Production

↓

Version Update

---

# Prompt Metrics

Track:

- Prompt Version
- Model Used
- Success Rate
- Average Latency
- Failure Rate
- User Satisfaction

---

# Summary

The Prompt Library ensures consistency, traceability, and continuous improvement of all AI interactions across H.I.R.E.