// Mock data — replace with live API responses once the backend endpoints in
// services/api.js are connected. Shapes here mirror the expected API contracts.

export const mockUser = {
  id: "cand_1042",
  name: "Ananya Rao",
  role: "candidate",
  title: "Frontend Engineer",
  email: "ananya.rao@example.com",
  location: "Bengaluru, IN",
  matchScore: 87,
  avatarInitials: "AR",
};

export const mockRecruiter = {
  id: "rec_0231",
  name: "Kabir Menon",
  role: "recruiter",
  company: "Northwind Labs",
  email: "kabir.menon@example.com",
  avatarInitials: "KM",
};

export const mockJobs = [
  {
    id: "job_101",
    title: "Frontend Engineer, Platform",
    company: "Northwind Labs",
    location: "Bengaluru, IN (Hybrid)",
    type: "Full-time",
    salaryRange: "₹18L – ₹26L",
    postedDaysAgo: 2,
    matchScore: 92,
    tags: ["React", "TypeScript", "Design Systems"],
    description:
      "Own the component library and performance budget for our recruiter-facing dashboard. Partner closely with design on a small, fast-moving team.",
    responsibilities: [
      "Build and maintain shared UI components used across three product surfaces",
      "Profile and improve rendering performance on data-heavy dashboard views",
      "Pair with design on interaction details and motion",
    ],
    requirements: [
      "3+ years building production React applications",
      "Comfort with accessibility and responsive layout fundamentals",
      "Experience with component-driven development",
    ],
  },
  {
    id: "job_102",
    title: "Product Designer, Hiring Tools",
    company: "Fieldstone AI",
    location: "Remote (India)",
    type: "Full-time",
    salaryRange: "₹16L – ₹22L",
    postedDaysAgo: 5,
    matchScore: 74,
    tags: ["Figma", "UX Research", "Systems"],
    description:
      "Shape the candidate experience for an AI interview product used by mid-size companies.",
    responsibilities: [
      "Run lightweight research with candidates and recruiters",
      "Design end-to-end flows from application to offer",
      "Maintain the design system alongside engineering",
    ],
    requirements: [
      "Portfolio showing end-to-end product design work",
      "Experience designing for complex, data-heavy products",
    ],
  },
  {
    id: "job_103",
    title: "Backend Engineer, Matching",
    company: "Northwind Labs",
    location: "Bengaluru, IN (Onsite)",
    type: "Full-time",
    salaryRange: "₹20L – ₹30L",
    postedDaysAgo: 1,
    matchScore: 61,
    tags: ["Node.js", "PostgreSQL", "ML Pipelines"],
    description:
      "Build the ranking service that scores candidate-job fit for recruiters using our platform.",
    responsibilities: [
      "Design and maintain the matching and ranking service",
      "Collaborate with the ML team on feature pipelines",
      "Own service reliability and observability",
    ],
    requirements: [
      "Strong backend fundamentals in a typed language",
      "Experience with relational databases at scale",
    ],
  },
  {
    id: "job_104",
    title: "Technical Recruiter",
    company: "Fieldstone AI",
    location: "Hyderabad, IN (Hybrid)",
    type: "Contract",
    salaryRange: "₹9L – ₹13L",
    postedDaysAgo: 8,
    matchScore: 45,
    tags: ["Sourcing", "ATS", "Interviewing"],
    description:
      "Run full-cycle recruiting for engineering roles across two product lines.",
    responsibilities: [
      "Source and screen candidates for open engineering roles",
      "Partner with hiring managers on role scoping",
      "Keep the pipeline and ATS records current",
    ],
    requirements: [
      "2+ years of technical recruiting experience",
      "Comfort working across multiple concurrent searches",
    ],
  },
];

export const mockApplications = [
  {
    id: "app_5001",
    jobId: "job_101",
    jobTitle: "Frontend Engineer, Platform",
    company: "Northwind Labs",
    appliedOn: "2026-07-10",
    stage: "Interview",
    stages: ["Applied", "Screening", "Interview", "Offer", "Hired"],
    currentStageIndex: 2,
  },
  {
    id: "app_5002",
    jobId: "job_102",
    jobTitle: "Product Designer, Hiring Tools",
    company: "Fieldstone AI",
    appliedOn: "2026-07-05",
    stage: "Screening",
    stages: ["Applied", "Screening", "Interview", "Offer", "Hired"],
    currentStageIndex: 1,
  },
  {
    id: "app_5003",
    jobId: "job_104",
    jobTitle: "Technical Recruiter",
    company: "Fieldstone AI",
    appliedOn: "2026-06-28",
    stage: "Not Selected",
    stages: ["Applied", "Screening", "Interview", "Offer", "Hired"],
    currentStageIndex: 1,
    rejected: true,
  },
];

export const mockCandidateStats = [
  { label: "Applications", value: 12 },
  { label: "Interviews", value: 4 },
  { label: "Offers", value: 1 },
  { label: "Profile match", value: "87%" },
];

export const mockRecruiterStats = [
  { label: "Open roles", value: 6 },
  { label: "Active candidates", value: 214 },
  { label: "Interviews this week", value: 18 },
  { label: "Avg. time to hire", value: "19 days" },
];

export const mockRecruiterCandidates = [
  { id: "cand_1042", name: "Ananya Rao", role: "Frontend Engineer", matchScore: 92, stage: "Interview" },
  { id: "cand_1043", name: "Devika Iyer", role: "Frontend Engineer", matchScore: 85, stage: "Screening" },
  { id: "cand_1044", name: "Rohit Verma", role: "Frontend Engineer", matchScore: 78, stage: "Applied" },
  { id: "cand_1045", name: "Sara Thomas", role: "Product Designer", matchScore: 71, stage: "Interview" },
];

export const mockInterviewQuestions = [
  {
    id: "q1",
    prompt: "Walk me through a project where you improved a slow-loading page. What did you measure first?",
  },
  {
    id: "q2",
    prompt: "Tell me about a time you disagreed with a design decision. How did you resolve it?",
  },
  {
    id: "q3",
    prompt: "How do you decide when a component should be broken into smaller pieces?",
  },
];
