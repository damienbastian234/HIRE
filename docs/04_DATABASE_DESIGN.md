# H.I.R.E.
# 04_DATABASE_DESIGN.md

---

# Human-Interactive Intelligent Recruitment Engine

## Version

1.0.0 (Sprint 0)

---

# Purpose

This document defines the database architecture of H.I.R.E.

It serves as the blueprint for the PostgreSQL database used by the platform and documents every entity, relationship, constraint, and design principle.

The database is designed to support the Hackathon MVP while remaining extensible for future startup features.

---

# Database Philosophy

H.I.R.E. uses a relational database because recruitment data contains many structured relationships between users, resumes, interviews, recommendations, and reports.

The database is designed using the following principles:

- Normalized structure (up to Third Normal Form where appropriate)
- Data integrity through foreign key constraints
- Minimal redundancy
- Scalability for future modules
- Clear and consistent naming conventions

---

# Database Management System

Primary Database:

PostgreSQL

---

# Why PostgreSQL?

PostgreSQL was selected because it provides:

- ACID compliance
- Excellent relational modeling
- Strong indexing capabilities
- High reliability
- Open-source licensing
- Excellent Python support
- Scalability for production deployment

---

# Naming Conventions

## Tables

- Singular names
- Snake case

Example:

user

resume

skill

interview_session

---

## Columns

Snake case

Examples:

user_id

created_at

career_score

resume_id

---

## Primary Keys

Every table uses

id

(UUID in production, Integer during initial development if preferred)

---

## Foreign Keys

Always use:

<entity>_id

Example:

user_id

resume_id

session_id

---

# Core Entities

The Hackathon MVP consists of the following primary entities:

User

↓

Profile

↓

Resume

↓

Skill

↓

Career Report

↓

Interview Session

↓

Interview Question

↓

Interview Response

↓

Recommendation

---

# Entity Relationship Overview

```

                  User
                    │
         ┌──────────┼───────────┐
         ▼          ▼           ▼
     Profile     Resume     Interview Session
                    │               │
                    ▼               ├──────────────┐
                 Skill             ▼              ▼
                              Question       Response

                    │
                    ▼
             Career Report
                    │
                    ▼
             Recommendation

```

---

# Table Definitions

## User

Purpose:

Stores authentication information.

| Column | Type | Constraints |
|----------|----------|-------------|
| id | UUID | PK |
| email | VARCHAR | UNIQUE |
| password_hash | TEXT | NOT NULL |
| role | VARCHAR | NOT NULL |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

---

## Profile

Purpose:

Stores personal information.

| Column | Type |
|----------|------|
| id | UUID |
| user_id | UUID FK |
| first_name | VARCHAR |
| last_name | VARCHAR |
| phone | VARCHAR |
| college | VARCHAR |
| degree | VARCHAR |
| graduation_year | INTEGER |
| career_goal | TEXT |

---

## Resume

Purpose:

Stores uploaded resume metadata.

| Column | Type |
|----------|------|
| id | UUID |
| user_id | UUID FK |
| file_name | TEXT |
| file_path | TEXT |
| upload_date | TIMESTAMP |
| parsing_status | VARCHAR |

---

## Skill

Purpose:

Stores extracted skills.

| Column | Type |
|----------|------|
| id | UUID |
| resume_id | UUID FK |
| skill_name | VARCHAR |
| skill_category | VARCHAR |
| confidence_score | DECIMAL |

---

## Career Report

Purpose:

Stores AI-generated career analysis.

| Column | Type |
|----------|------|
| id | UUID |
| user_id | UUID FK |
| career_score | DECIMAL |
| strengths | JSONB |
| weaknesses | JSONB |
| skill_gaps | JSONB |
| generated_at | TIMESTAMP |

---

## Recommendation

Purpose:

Stores personalized recommendations.

| Column | Type |
|----------|------|
| id | UUID |
| report_id | UUID FK |
| recommendation_type | VARCHAR |
| title | VARCHAR |
| description | TEXT |
| priority | VARCHAR |

---

## Interview Session

Purpose:

Stores interview attempts.

| Column | Type |
|----------|------|
| id | UUID |
| user_id | UUID FK |
| interview_type | VARCHAR |
| started_at | TIMESTAMP |
| completed_at | TIMESTAMP |
| total_score | DECIMAL |

---

## Interview Question

Purpose:

Stores generated interview questions.

| Column | Type |
|----------|------|
| id | UUID |
| session_id | UUID FK |
| question | TEXT |
| category | VARCHAR |
| difficulty | VARCHAR |

---

## Interview Response

Purpose:

Stores candidate responses.

| Column | Type |
|----------|------|
| id | UUID |
| question_id | UUID FK |
| response | TEXT |
| score | DECIMAL |
| feedback | TEXT |

---

# Relationships

User → Profile

One-to-One

---

User → Resume

One-to-Many

---

Resume → Skill

One-to-Many

---

User → Interview Session

One-to-Many

---

Interview Session → Interview Question

One-to-Many

---

Interview Question → Interview Response

One-to-One

---

User → Career Report

One-to-Many

---

Career Report → Recommendation

One-to-Many

---

# Indexing Strategy

Indexes will be created on:

email

user_id

resume_id

session_id

created_at

career_score

---

# Constraints

The database enforces:

- Primary Keys
- Foreign Keys
- Unique email addresses
- NOT NULL constraints where applicable
- Cascading deletes for dependent records
- Timestamp tracking

---

# Future Database Expansion

The architecture supports future tables for:

- Recruiters
- Companies
- Universities
- Placement Officers
- Robot Sessions
- Job Matching
- Learning Progress
- Notifications
- Analytics
- Audit Logs

These tables are intentionally excluded from the Hackathon MVP but can be integrated without redesigning the existing schema.

---

# Summary

The H.I.R.E. database follows a normalized relational design that emphasizes data integrity, scalability, and maintainability.

The schema supports all Hackathon MVP features while providing a solid foundation for future startup expansion.