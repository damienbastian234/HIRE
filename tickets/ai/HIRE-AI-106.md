HIRE-AI-106 — Resume Analysis API
Objective
Implement the first production AI endpoint for H.I.R.E.:

```
POST /api/v1/resume/analyze
```

This endpoint must expose the existing AI framework through a FastAPI API.
This ticket is application-layer orchestration only.
Do not implement any new AI logic.
Do not modify the AI framework.
Do not modify existing engines.
Reuse everything that already exists.
Existing Components (Reuse Only)
Reuse the existing implementation exactly as it exists.
AI Framework:

* BaseEngine
* AIContext
* EngineRegistry
* AIOrchestrator
* IntelligenceResult
* WorkflowResult

AI Engines:

* ResumeIntelligenceEngine
* SkillIntelligenceEngine
* ExperienceIntelligenceEngine
* CandidateMatchingEngine

Resume Parser:

* Existing parser modules

Models:

* CandidateProfile
* JobRequirement
* CandidateMatching
* SkillIntelligence
* ExperienceIntelligence

Response Schema:

* SuccessResponse

Exceptions:

* Existing AIException hierarchy

Do not duplicate any logic already implemented inside these components.
Architectural Constraints
The framework remains unchanged.
Specifically:

* Do not modify BaseEngine.
* Do not modify AIOrchestrator.
* Do not add automatic context propagation.
* Do not modify any engine to write into `context.data`.

The service layer is responsible for wiring engine outputs into downstream engine inputs.
The orchestration should follow this pattern:

```
resume_result = await resume_engine.run(context)

candidate_profile = CandidateProfile(**resume_result.output)

context.data["candidate_profile"] = candidate_profile

workflow_result = await orchestrator.run(
    context,
    [
        "skill_intelligence",
        "experience_intelligence",
        "candidate_matching",
    ],
)
```

Populate:

```
context.data["resume_text"]
```

before ResumeIntelligenceEngine.
Populate:

```
context.data["job_requirement"]
```

before CandidateMatchingEngine.
This wiring belongs only in the application/service layer.
Endpoint
Implement:

```
POST /api/v1/resume/analyze
```

The endpoint must:

1. Receive resume input.
2. Parse the request.
3. Build AIContext.
4. Register the existing engines.
5. Execute ResumeIntelligenceEngine.
6. Bridge CandidateProfile into context.
7. Execute the remaining engines through AIOrchestrator.
8. Aggregate the results.
9. Return a SuccessResponse.

Request Model
Create any request schema required for this endpoint.
Only create schemas that do not already exist.
Response
Return a single aggregated response containing:

* CandidateProfile
* Skill Intelligence
* Experience Intelligence
* Candidate Matching

wrapped in the project's existing SuccessResponse envelope.
Do not invent a new response format.
Error Handling
Reuse the existing exception framework.
Do not introduce new exception behavior.
Validation failures must use the existing validation exceptions.
Unexpected failures must use the existing AI exception hierarchy.
Testing
Create comprehensive tests covering:

* Successful resume analysis
* Invalid request
* Missing resume
* Engine failure propagation
* Service orchestration
* Response structure

Reuse the existing testing style.
Code Quality
Before completion:
Run:

```
python -m ruff check .
```

Run:

```
python -m pytest -q
```

Both must pass.
Deliverables
Provide:

1. Files created
2. Files modified
3. Exact responsibilities of each file
4. Why each change was necessary
5. Ruff results
6. Pytest results
7. Confirmation that:
   * No AI framework behavior changed.
   * No engine logic changed.
   * No parser logic changed.
   * No business logic was duplicated.
   * The implementation is strictly application-layer orchestration using the existing H.I.R.E. architecture.