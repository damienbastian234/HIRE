/**
 * H.I.R.E. — Frontend API client
 *
 * Responsibilities:
 *  - Auth store  (token + user in localStorage, single source of truth)
 *  - Shared error parser (handles all backend error shapes)
 *  - Authenticated HTTP client (adds Bearer header automatically)
 *  - Typed API surface matching backend Pydantic schemas exactly
 */

const API_BASE   = import.meta.env.VITE_API_TARGET || 'http://127.0.0.1:8000'
const API_PREFIX = `${API_BASE}/api/v1`

// ─── Core User Types ──────────────────────────────────────────────────────────
export type Role = 'candidate' | 'recruiter'
export type User = { id: string; name: string; email: string; role: Role }
export type Job  = {
  id: string; title: string; company: string; location: string
  type: string; salary: string; description: string
}
export type Profile = { name: string; title: string; email: string; location: string; role: Role }
export type Stat    = { label: string; value: string | number }
export type Application = {
  id: string; jobId: string; jobTitle?: string; company?: string
  status: string; updatedAt: string
}
export type CandidateDashboard = { applications: Application[]; stats: Stat[] }
export type RecruiterDashboard = {
  company: string; stats: Stat[]
  candidates: { name: string; stage: string; skillMatch: number }[]
}

// ─── Mock Interview Types ──────────────────────────────────────────────────────
export type InterviewQuestion = {
  id: number
  type: 'behavioural' | 'situational' | 'technical' | 'motivation'
  question: string
  hint: string
}
export type InterviewEvaluation = {
  score: number
  verdict: string
  strengths: string[]
  improvements: string[]
  model_answer: string
  tip: string
}

// ─── Job Requirement Types (mirrors backend models/job_requirement.py) ─────────
export type WorkMode       = 'ONSITE' | 'REMOTE' | 'HYBRID'
export type EmploymentType = 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERN' | 'FREELANCE' | 'TEMPORARY'

export type SkillRequirement = {
  name: string; required?: boolean; minimum_proficiency?: string; minimum_years?: number
}
export type ExperienceRequirement = { minimum_years: number; preferred_years?: number }
export type EducationRequirement  = {
  degrees?: string[]; fields_of_study?: string[]
  minimum_percentage?: number; minimum_cgpa?: number
}
export type SalaryRange    = { minimum?: number; maximum?: number; currency?: string }
export type JobRequirement = {
  title: string; department?: string; company?: string; location?: string
  work_mode?: WorkMode; employment_type?: EmploymentType; description?: string
  responsibilities?: string[]; required_skills?: SkillRequirement[]
  preferred_skills?: SkillRequirement[]; experience?: ExperienceRequirement
  education?: EducationRequirement; salary?: SalaryRange; keywords?: string[]
}

// ─── Analysis Output Types (mirrors all backend intelligence models) ──────────
export type TimelineEntry = {
  company?: string; position?: string; start_year?: number; start_month?: number
  end_year?: number; end_month?: number; is_current: boolean
  duration_months?: number; has_valid_dates: boolean
}
export type CareerMove    = {
  from_company?: string; from_position?: string
  to_company?: string;   to_position?: string; move_type: string
}
export type EmploymentGap = { after_company?: string; before_company?: string; gap_months: number }

export type Analysis = {
  candidate_profile: {
    personal_info: {
      full_name?: string; email?: string; phone?: string
      linkedin_url?: string; github_url?: string; portfolio_url?: string; location?: string
    }
    education: {
      degree?: string; institution?: string; specialization?: string
      gpa?: string; graduation_year?: string
    }[]
    experience: {
      company?: string; position?: string; employment_type?: string
      start_date?: string; end_date?: string; duration?: string; responsibilities: string[]
    }[]
    skills:         { technical_skills: string[]; soft_skills: string[] }
    projects:       { name?: string; description?: string; technologies: string[] }[]
    certifications: { name?: string; organization?: string; completion_date?: string }[]
    languages:      string[]
  }
  skill_intelligence: {
    categories:       { name: string; skills: string[]; confidence: number }[]
    metrics: {
      technical_skill_count: number; soft_skill_count: number; total_skills: number
      categorized_skills: number; uncategorized_skills: number
    }
    gaps:             { missing_categories: string[]; recommendations: string[] }
    normalized_skills: string[]
    duplicate_skills:  string[]
  }
  experience_intelligence: {
    timeline: { entries: TimelineEntry[] }
    metrics: {
      total_experience_months: number; total_experience_years: number
      company_count: number; average_tenure_months?: number
      longest_tenure_months?: number; shortest_tenure_months?: number
      is_currently_employed: boolean
    }
    progression: { moves: CareerMove[]; overall_trend: string }
    gap_analysis: { gaps: EmploymentGap[]; gap_count: number; total_gap_months: number }
    stability: {
      stability_score: number; average_tenure_months?: number
      job_change_count: number; longest_tenure_months?: number
    }
    seniority_level: string
  }
  candidate_matching: {
    skill_match: {
      matched_required_skills: string[]; missing_required_skills: string[]
      matched_preferred_skills: string[]
      required_match_percentage: number; preferred_match_percentage: number
    }
    experience_match: {
      required_years: number; candidate_years: number
      meets_requirement: boolean; experience_match_percentage: number
    }
    education_match: {
      required_degree?: string; candidate_degree?: string; meets_requirement: boolean
    }
    overall_score: {
      skill_score: number; experience_score: number
      education_score: number; overall_score: number
    }
    recommendation: string
    confidence:     number
  }
}

// ─── Auth Store ───────────────────────────────────────────────────────────────
const TOKEN_KEY = 'hire-token'
const USER_KEY  = 'hire-user'

export const authStore = {
  getToken: ()             => localStorage.getItem(TOKEN_KEY) ?? '',
  setToken: (t: string)   => localStorage.setItem(TOKEN_KEY, t),
  getUser:  ()             => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') as User | null }
    catch { return null }
  },
  setUser:  (u: User)     => localStorage.setItem(USER_KEY, JSON.stringify(u)),
  clearAuth: ()            => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
  isLoggedIn: ()           => Boolean(localStorage.getItem(TOKEN_KEY)),
}

// ─── Error Parser ─────────────────────────────────────────────────────────────
// Handles all known backend error shapes:
//   { success: false, error: { type, message } }   ← HireException / HTTPException
//   { detail: "string" }                            ← raw FastAPI HTTPException
//   { detail: [{ msg, loc }] }                      ← Pydantic validation array
//   { message: "string" }                           ← legacy shape
//   network failure (TypeError / fetch error)
export function parseError(err: unknown): string {
  if (err instanceof TypeError) return 'Cannot connect to the H.I.R.E. backend. Make sure the server is running.'
  if (!(err instanceof Error)) return 'An unexpected error occurred.'
  return err.message
}

function extractMessage(body: Record<string, unknown>, status: number): string {
  // Structured H.I.R.E. error envelope: { success: false, error: { type, message } }
  if (body.error && typeof body.error === 'object') {
    const e = body.error as Record<string, unknown>
    if (typeof e.message === 'string') return e.message
  }
  // FastAPI HTTPException string detail
  if (typeof body.detail === 'string') return body.detail
  // FastAPI validation error array
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((d: { msg?: string; loc?: string[] }) =>
        [d.loc?.slice(1).join('.'), d.msg].filter(Boolean).join(': '))
      .join('; ')
  }
  // Legacy { message }
  if (typeof body.message === 'string') return body.message
  return `Request failed (${status})`
}

// ─── HTTP Client ──────────────────────────────────────────────────────────────
async function request<T>(
  path: string,
  options: RequestInit = {},
  requireAuth = true,
  signal?: AbortSignal,
): Promise<T> {
  const headers: Record<string, string> = {}

  // Only set Content-Type for non-FormData bodies
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  if (requireAuth) {
    const token = authStore.getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string> || {}) },
    signal,
  })

  // Centralized 401 handling — clear stale auth state and redirect to login.
  if (response.status === 401 && requireAuth) {
    authStore.clearAuth()
    // Reload the page so App.tsx re-evaluates auth state and shows login.
    window.location.reload()
    // Throw so calling code never sees a partial result after the reload.
    throw new Error('Session expired. Please log in again.')
  }

  const body: Record<string, unknown> = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(extractMessage(body, response.status))
  }
  return body as T
}

// ─── API Surface ──────────────────────────────────────────────────────────────
export const api = {
  // ── Health (unauthenticated) ──────────────────────────────────────────────
  health: () =>
    request<{ status: string }>('/health', {}, false),

  // ── Auth ─────────────────────────────────────────────────────────────────
  login: (payload: { email: string; password: string }) =>
    request<{ token: string; user: User }>('/auth/login', {
      method: 'POST', body: JSON.stringify(payload),
    }, false),

  register: (payload: { name: string; email: string; password: string; role: Role }) =>
    request<{ token: string; user: User }>('/auth/register', {
      method: 'POST', body: JSON.stringify(payload),
    }, false),

  me: () => request<User>('/auth/me'),

  resetPassword: (payload: { email: string; new_password: string }) =>
    request<{ success: boolean; message: string }>('/auth/reset-password', {
      method: 'POST', body: JSON.stringify(payload),
    }, false),

  // ── AI Chatbot ────────────────────────────────────────────────────────────
  chat: (messages: { role: 'user' | 'model'; content: string }[]) =>
    request<{ reply: string }>('/chat', {
      method: 'POST', body: JSON.stringify({ messages }),
    }),

  // ── Mock Interview ────────────────────────────────────────────────────────
  generateInterviewQuestions: (payload: {
    job_role: string; difficulty: string; num_questions: number
  }) =>
    request<{ questions: InterviewQuestion[]; job_role: string; difficulty: string }>(
      '/interview/generate', { method: 'POST', body: JSON.stringify(payload) }
    ),

  evaluateAnswer: (payload: {
    job_role: string; question_id: number; question_text: string;
    question_type: string; answer: string;
  }) =>
    request<{ evaluation: InterviewEvaluation; question_id: number }>(
      '/interview/evaluate', { method: 'POST', body: JSON.stringify(payload) }
    ),

  // ── Profile ───────────────────────────────────────────────────────────────
  profile: () => request<Profile>('/profile'),

  updateProfile: (payload: Partial<Profile>) =>
    request<{ success: boolean; profile: Profile }>('/profile', {
      method: 'PUT', body: JSON.stringify(payload),
    }),

  // ── Jobs ──────────────────────────────────────────────────────────────────
  jobs: () => request<{ jobs: Job[]; total: number }>('/jobs'),

  job: (id: string) => request<{ job: Job }>(`/jobs/${id}`),

  apply: (jobId: string) =>
    request<{ success: boolean; message: string; applicationId: string }>(
      `/jobs/${jobId}/apply`, { method: 'POST' },
    ),

  // ── Dashboard ─────────────────────────────────────────────────────────────
  dashboard: (role: Role) =>
    request<CandidateDashboard | RecruiterDashboard>(`/dashboard/${role}`),

  // ── Applications ──────────────────────────────────────────────────────────
  application: (id: string) => request<Application>(`/applications/${id}`),

  // ── Recruiter ─────────────────────────────────────────────────────────────
  recruiterCandidates: () =>
    request<{
      candidates: { name: string; stage: string; skillMatch: number; email: string }[]
      note: string
    }>('/recruiter/candidates'),

  // ── Resume Intelligence ───────────────────────────────────────────────────
  analyze: (
    resume_text: string,
    job_requirement: JobRequirement,
    signal?: AbortSignal,
  ) =>
    request<{ success: boolean; message: string; data: Analysis }>(
      '/resume/analyze',
      { method: 'POST', body: JSON.stringify({ resume_text, job_requirement }) },
      true,
      signal,
    ),

  extractResume: async (
    file: File,
    signal?: AbortSignal,
  ): Promise<{ filename: string; text: string }> => {
    const body = new FormData()
    body.append('file', file)
    const token = authStore.getToken()
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const response = await fetch(`${API_PREFIX}/resume/extract`, {
      method: 'POST', body, headers, signal,
    })
    // 401 on file upload: clear auth and reload.
    if (response.status === 401) {
      authStore.clearAuth()
      window.location.reload()
      throw new Error('Session expired. Please log in again.')
    }
    const result: Record<string, unknown> = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(extractMessage(result, response.status))
    return result as { filename: string; text: string }
  },
}