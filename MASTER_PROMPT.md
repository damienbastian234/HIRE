# HIRE Project Master Engineering Prompt

You are a senior full-stack engineer responsible for bringing this HIRE project from demo-quality to a secure, reliable, production-ready application. Work in the existing repository and preserve unrelated user changes. Do not hide, weaken, or bypass failing tests; update tests when the intended behavior changes.

## Project Context

- Backend: FastAPI/Python in `backend/`, with AI engines, resume parsing, authentication, and demo routes.
- Frontend: React/TypeScript/Vite in `frontend/`.
- Product roles: candidate and recruiter.
- The repository documentation describes PostgreSQL, SQLAlchemy/Alembic, bcrypt, JWT authentication, resume analysis, candidate matching, jobs, applications, and intelligence modules.
- Current implementation still contains demo shortcuts, process-local storage, incomplete authorization, and frontend/API contract drift.

## Identified Errors That Must Be Rectified

Treat the following as confirmed defects found during the backend and frontend audit. Do not treat them as optional enhancements.

| Area | Identified error | Consequence | Required rectification |
| --- | --- | --- | --- |
| Login | Existing emails can log in with any password, and unknown emails are automatically registered. | Account takeover and unrestricted account creation. | Hash passwords, verify credentials, reject invalid login attempts with HTTP 401, and remove login-time registration. |
| Roles | Profile updates can change the user's role, recruiter routes lack role checks, and dashboard behavior trusts the URL role. | Candidate-to-recruiter privilege escalation and unauthorized data access. | Make roles server-controlled, enforce reusable role dependencies, and derive access from the authenticated user. |
| Resume security | Resume extraction and analysis are unauthenticated. | Anonymous users can upload personal data and consume processing resources. | Require authentication, authorization, quotas, and safe error handling. |
| Upload limits | `MAX_UPLOAD_SIZE_MB` is configured but the route reads the complete file without enforcing it. | Oversized uploads can exhaust memory or cause denial of service. | Stream or bounded-read uploads and return HTTP 413 when the limit is exceeded. |
| File parsing | `.doc` is accepted but treated as UTF-8 text instead of being parsed as a legacy binary document. | Corrupt, empty, or misleading resume extraction. | Remove `.doc` support or add a real parser/conversion path. |
| Error disclosure | Parser exception strings are returned directly to clients. | Internal paths, library details, and implementation information may leak. | Log details server-side and return stable client-safe messages. |
| Identity | Profile email changes update a profile separately from the canonical user record. | JWT, login identity, `/auth/me`, and profile data can disagree. | Make email immutable or implement verified email change with token invalidation. |
| Persistence | Users, profiles, and applications are stored in process-local dictionaries. | Data disappears on restart and differs between workers. | Implement database-backed persistence, migrations, transactions, and repositories. |
| API contract | Documentation, backend error envelopes, registration responses, and frontend types do not agree. | Frontend failures are misinterpreted and integrations are brittle. | Define one contract, update OpenAPI/docs, and add contract validation. |
| Request cancellation | `Intelligence.tsx` aborts a controller that is never passed to `api.analyze()`. | Stale analysis requests can overwrite newer results and waste resources. | Pass `AbortSignal` through the API client and ignore cancelled/stale responses. |
| Authentication state | Frontend has no consistent timeout, non-JSON handling, or centralized 401 cleanup. | Users can remain in stale sessions and receive unclear failures. | Centralize request/error handling and clear invalid authentication state. |
| Recruiter data | Dashboard counts and candidate records come from inconsistent/static sources. | Recruiters see misleading metrics and non-authoritative candidate data. | Use one persisted source, or explicitly isolate and label fixture/demo data. |
| Configuration | Debug defaults, predictable demo secrets, permissive operational assumptions, and incomplete migration setup remain. | Production deployment can expose secrets, data, and unsafe behavior. | Validate configuration at startup, rotate secrets, restrict CORS, add security headers, and make migrations real. |
| Startup | `start.js` and `run.ps1` select environments and readiness checks differently; `start.js` can kill unrelated processes. | Developers get inconsistent or destructive startup behavior. | Consolidate startup behavior, use the selected virtual environment, and poll `/health`. |
| CSS | An empty `.candidate-card` ruleset and vendor-only `-moz-appearance` diagnostic remain. | Stylesheet quality and browser compatibility are reduced. | Remove the empty rule and use the standard `appearance` property. |

The implementation must add regression tests for every rectified defect. Existing tests that encode insecure demo behavior, especially automatic account creation during login, must be changed to assert the secure behavior.

## Feature Improvements Required

After the defects above are controlled, improve the product in these areas:

### Candidate Experience

- Provide a complete candidate profile with validated personal information, education, experience, skills, certifications, languages, projects, and resume history.
- Support secure resume upload, extraction, analysis, replacement, deletion, and analysis-result history.
- Show clear progress, empty, success, cancellation, validation, authentication, and failure states.
- Present AI findings with confidence/context where available, explain missing information, and allow the candidate to correct extracted data.
- Add candidate-facing job discovery, filtering, pagination, job details, application submission, application status, and application history.

### Recruiter Experience

- Provide recruiter-only job creation, editing, publishing, closing, and ownership enforcement.
- Add candidate search, filtering, pagination, profile viewing, resume/analysis viewing, and comparison based on persisted data.
- Add application review workflows with controlled statuses, notes, audit history, and recruiter ownership checks.
- Replace misleading static dashboard values with authoritative metrics for open jobs, applicants, pipeline stages, and recent activity.
- Add useful empty states and permission-aware error states instead of silently hiding failures.

### AI And Matching Quality

- Persist normalized resume data and analysis results with versioning and timestamps.
- Validate every AI response against schemas before storage or display.
- Make provider/model configuration explicit and provide deterministic fallback behavior when an AI provider is unavailable.
- Improve candidate-job matching with explainable match factors, missing requirements, strengths, confidence, and configurable weighting.
- Prevent duplicate analysis work, support retries, and expose analysis status without blocking the entire UI.
- Add observability for latency, provider failures, parsing failures, and analysis outcomes without logging sensitive resume content.

### Platform Quality

- Generate or contract-test frontend API types from the backend OpenAPI schema.
- Add accessible keyboard/focus behavior, semantic form labels, responsive layouts, and announced errors throughout the frontend.
- Add pagination, filtering, sorting, debounced search, optimistic updates only where safe, and clear refresh behavior for data-heavy screens.
- Add audit logs, health/readiness checks, rate limiting, security headers, structured logging, and deployment documentation.
- Add frontend unit/component tests, backend integration tests, API contract tests, and browser-level candidate/recruiter smoke tests.

## First: Establish A Baseline

1. Inspect the current working tree and preserve unrelated modifications.
2. Run the complete backend test suite with coverage.
3. Run the frontend install/typecheck/build commands from `frontend/`.
4. Capture the current failures and distinguish existing failures from regressions introduced by your work.
5. Read the relevant backend tests before changing behavior. Existing tests that require insecure demo behavior must be replaced with tests for the secure behavior below.

## Critical Security Corrections

### Authentication

Fix the authentication implementation in `backend/app/api/routes/demo.py` and its supporting services:

- Store a password hash using the project's approved bcrypt or Argon2 approach; never store plaintext passwords.
- Verify the submitted password during login.
- Return the same safe unauthorized response for an unknown email and an invalid password.
- Remove automatic account creation from the login endpoint.
- Validate email format and enforce a reasonable password policy.
- Keep JWT claims minimal, validate expiration and signing configuration, and never use a predictable production secret.
- Add tests for registration, successful login, wrong password, unknown email, malformed credentials, expired tokens, and `/auth/me`.

### Authorization

- Treat the server-side role as authoritative.
- Do not allow `PUT /profile` or any client payload to change a user's role.
- Add a reusable `require_role("candidate")` / `require_role("recruiter")` dependency or equivalent.
- Protect recruiter candidate lists, recruiter dashboards, job management, and application-management actions with recruiter authorization.
- Protect candidate-only actions with candidate authorization where applicable.
- Validate dashboard role from the authenticated user instead of trusting `/dashboard/{role}`.
- Ensure object-level authorization: users may only view or mutate their own profile, resume, applications, and analysis unless explicitly authorized.
- Add tests proving that a candidate cannot become a recruiter, access recruiter endpoints, spoof the dashboard role, or access another user's data.

### Resume Uploads And Analysis

Secure both extraction and analysis endpoints in `backend/app/api/routes/resume.py`:

- Require authentication for `/resume/extract` and `/resume/analyze`.
- Enforce `MAX_UPLOAD_SIZE_MB` while reading the upload; reject oversized files with HTTP 413.
- Validate extension, MIME type, and file signature where practical; do not trust the filename alone.
- Avoid unbounded `await file.read()` and avoid loading unnecessarily large files into memory.
- Either remove `.doc` from accepted formats or implement a real legacy `.doc` parser/conversion path. Do not decode binary `.doc` files as UTF-8.
- Return stable, client-safe parsing errors; log detailed exception information only on the server.
- Add request quotas/rate limiting and sensible processing timeouts.
- Add tests for authentication, size boundaries, malformed PDF/DOCX, unsupported formats, parser failure, and successful extraction.

## Replace Demo Persistence

The current process-global dictionaries for users, profiles, and applications are not acceptable beyond a single-process demo.

- Implement the documented database-backed persistence using the existing SQLAlchemy/PostgreSQL direction, or clearly document and enforce an explicit alternative.
- Add canonical user, profile, job, application, resume, and analysis persistence as required by existing models and routes.
- Store password hashes and role data in the database.
- Add repository/service boundaries, transaction handling, constraints, indexes, and migrations.
- Ensure data survives restart and is consistent across workers.
- Remove or isolate mutable in-memory stores from production code.
- Add persistence/restart tests and tests for concurrent or repeated requests where relevant.

## Identity And Profile Correctness

- Make email immutable, or implement a verified email-change workflow that updates the canonical user record and invalidates/reissues tokens.
- Do not update a profile email independently of the user identity record.
- Ensure `/auth/me`, `/profile`, JWT claims, and database records agree after every supported profile operation.
- Reject duplicate email registration and handle race conditions at the database level.

## Frontend/API Integration

Inspect `frontend/src/api.ts`, `Intelligence.tsx`, authentication state, and all pages that call the backend.

- Add optional `AbortSignal` support to API methods and actually pass the signal into `fetch`; the current intelligence abort controller is created but not connected to the request.
- Add request timeouts and make cancellation distinguishable from ordinary errors.
- Prevent stale analysis responses from overwriting newer analysis state.
- Centralize 401 handling: clear invalid auth state, redirect to login when appropriate, and avoid loops.
- Handle non-JSON responses and network failures safely.
- Reconcile frontend types and backend response envelopes. The documented error shape differs from the current `{ success, error: { type, message } }` implementation, and registration response documentation differs from the actual `{ token, user }` response.
- Prefer generated TypeScript types from OpenAPI, or add contract tests that fail when backend schemas and frontend types drift.
- Keep loading, empty, success, cancellation, unauthorized, validation, parser-error, and server-error states explicit in every data-heavy view.
- Do not rely on hidden navigation or client-side checks for authorization.

## Recruiter Dashboard And Product Completeness

- Replace static recruiter candidate records and inconsistent application-derived counts with one authoritative data source.
- If fixtures remain for demo mode, label them explicitly and isolate them from production behavior.
- Complete job CRUD, application lifecycle/status handling, candidate search/filtering, pagination, and recruiter ownership checks as required by the documented product scope.
- Persist resume analysis results and expose stable status/progress/error states.
- Ensure AI engines fail gracefully when optional providers or model configuration are unavailable.
- Validate AI output schemas before storing or displaying results.
- Add audit logging for authentication, role-sensitive actions, uploads, and application status changes.

## API, Configuration, And Operations

- Make OpenAPI schemas, response models, `docs/05_API_SPECIFICATION.md`, and actual routes agree. Choose one canonical error envelope and apply it consistently.
- Remove `DEBUG=True` defaults and predictable demo secrets from production configuration.
- Validate required environment variables at startup and document safe development defaults.
- Confirm `.env` is ignored and has never been committed; rotate any exposed or predictable secret.
- Configure CORS from an explicit allowlist, not a permissive wildcard in credentialed mode.
- Add rate limiting, security headers, HTTPS guidance, secure cookie/token storage guidance, and secret rotation documentation.
- Add a usable Alembic migration setup if migrations are documented.
- Return health/readiness information that verifies the dependencies the application needs.

## Startup And Build Consistency

Unify `start.js` and `run.ps1`:

- Use the same selected Python virtual environment and dependency installation assumptions.
- Use the same reload and environment behavior in development.
- Do not kill every process found on ports 8000 and 5173; only stop processes owned by the project or fail with a clear message.
- Poll a real `/health` endpoint rather than only checking whether a TCP port is open.
- Verify frontend dependencies before starting Vite.
- Document one recommended development command and one production deployment path.
- Keep generated `frontend/dist` output out of source-of-truth workflows unless explicitly required.

## Frontend Quality Fixes

- Fix the empty `.candidate-card {}` ruleset in `frontend/src/styles.css`.
- Add the standard `appearance` property alongside or instead of `-moz-appearance` where needed.
- Check responsive layouts, keyboard navigation, focus states, semantic labels, error announcements, and mobile behavior.
- Keep the existing visual language, but ensure every interactive control has a complete functional state rather than being decorative.

## Required Test Coverage

Add or update focused tests for:

- Password hashing and verification.
- Unknown and invalid login credentials.
- JWT expiration and invalid signatures.
- Candidate/recruiter authorization and object ownership.
- Role spoofing and profile role mutation.
- Resume endpoint authentication, upload limits, MIME/signature validation, malformed files, and safe errors.
- Email-change or immutable-email behavior.
- Database persistence across restart and transaction rollback/error paths.
- CORS and security configuration.
- Consistent API success/error response schemas.
- Frontend API cancellation, stale-request protection, 401 handling, and representative loading/error states.
- End-to-end candidate and recruiter workflows.

## Definition Of Done

The work is complete only when:

1. Backend tests pass, including the new security and integration tests.
2. Frontend typecheck, lint, and production build pass.
3. Candidate and recruiter workflows have been manually or browser-tested against the running backend.
4. No endpoint relies on client-side authorization.
5. No password, token, or sensitive resume data is logged or returned in an unsafe form.
6. API docs and generated/handwritten frontend types match the implementation.
7. Startup, environment, migration, and deployment instructions are accurate.
8. The final response lists changed files, tests run, remaining limitations, and any migration or environment steps required.

Work in small, reviewable increments. After each substantive change, run the narrowest relevant test first, then the complete validation suite before declaring the project finished.