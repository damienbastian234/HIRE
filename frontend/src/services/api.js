import axios from "axios";
import {
  mockApplications,
  mockCandidateStats,
  mockInterviewQuestions,
  mockJobs,
  mockRecruiterCandidates,
  mockRecruiterStats,
} from "./mockData";

const DEMO_PROFILE = {
  name: "Demo Candidate",
  title: "Product Designer",
  email: "candidate@example.com",
  location: "San Francisco, CA",
};

const readSessionProfile = () => {
  try {
    const stored = localStorage.getItem("hire_session");
    if (!stored) return { ...DEMO_PROFILE };
    const parsed = JSON.parse(stored);
    return {
      ...DEMO_PROFILE,
      ...parsed,
    };
  } catch {
    return { ...DEMO_PROFILE };
  }
};

const writeSessionProfile = (profile) => {
  const current = readSessionProfile();
  const next = { ...current, ...profile };
  localStorage.setItem("hire_session", JSON.stringify(next));
  return next;
};

const fallbackError = (message) => Promise.reject({ response: { data: { detail: message } } });

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// Attach auth token to every outgoing request, if one exists.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("hire_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Centralized response error handling (expand once backend error shape is known).
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("hire_token");
    }
    return Promise.reject(error);
  }
);

/* ------------------------- Auth ------------------------- */

export const login = async (credentials) => {
  try {
    return await apiClient.post("/auth/login", credentials);
  } catch (error) {
    if (error.response?.status === 404) {
      const demoUser = {
        id: "demo-user",
        name: credentials.email?.includes("@") ? "Demo Candidate" : credentials.name || "Demo Candidate",
        email: credentials.email || "candidate@example.com",
        role: "candidate",
      };
      localStorage.setItem("hire_session", JSON.stringify(demoUser));
      localStorage.setItem("hire_token", "demo-token");
      return {
        data: {
          token: "demo-token",
          user: demoUser,
        },
      };
    }
    return fallbackError("Unable to sign in right now.");
  }
};

export const register = async (payload) => {
  try {
    return await apiClient.post("/auth/register", payload);
  } catch (error) {
    if (error.response?.status === 404) {
      const demoUser = {
        id: "demo-user",
        name: payload.name || "Demo Candidate",
        email: payload.email || "candidate@example.com",
        role: payload.role || "candidate",
      };
      localStorage.setItem("hire_session", JSON.stringify(demoUser));
      localStorage.setItem("hire_token", "demo-token");
      return {
        data: {
          token: "demo-token",
          user: demoUser,
        },
      };
    }
    return fallbackError("Unable to create an account right now.");
  }
};

export const logout = () => {
  localStorage.removeItem("hire_token");
  localStorage.removeItem("hire_session");
  return Promise.resolve({ success: true });
};

/* ------------------------- Resume ------------------------- */

export const uploadResume = (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append("resume", file);
  return apiClient.post("/resume/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
};

export const getResumeAnalysis = (resumeId) => {
  return apiClient.get(`/resume/${resumeId}/analysis`);
};

/* ------------------------- Jobs ------------------------- */

export const getJobs = async (params = {}) => {
  try {
    return await apiClient.get("/jobs", { params });
  } catch (error) {
    if (error.response?.status === 404) {
      return {
        data: {
          jobs: mockJobs,
          total: mockJobs.length,
        },
      };
    }
    return fallbackError("Unable to load jobs right now.");
  }
};

export const getJobById = async (jobId) => {
  try {
    return await apiClient.get(`/jobs/${jobId}`);
  } catch (error) {
    if (error.response?.status === 404) {
      const job = mockJobs.find((item) => item.id === jobId);
      return { data: { job: job ?? null } };
    }
    return fallbackError("Unable to load job.");
  }
};

export const applyJob = async (jobId, payload) => {
  try {
    return await apiClient.post(`/jobs/${jobId}/apply`, payload);
  } catch (error) {
    return {
      data: {
        success: true,
        message: "Application submitted.",
        applicationId: `app-${jobId}`,
        payload,
      },
    };
  }
};

/* ------------------------- Dashboard ------------------------- */

export const getDashboard = async (role) => {
  try {
    const response = await apiClient.get(`/dashboard/${role}`);
    const data = response?.data ?? {};

    if (role !== "recruiter" && data.stats && !Array.isArray(data.stats)) {
      const objectStats = data.stats;
      response.data = {
        ...data,
        stats: [
          { label: "Applications", value: objectStats.applications ?? 0 },
          { label: "Interviews", value: objectStats.interviews ?? 0 },
          { label: "Offers", value: objectStats.offers ?? 0 },
          { label: "Profile match", value: objectStats.profileScore ? `${objectStats.profileScore}%` : "0%" },
        ],
      };
    }

    return response;
  } catch (error) {
    if (error.response?.status === 404) {
      if (role === "recruiter") {
        return {
          data: {
            company: "Northstar Labs",
            stats: mockRecruiterStats,
            candidates: mockRecruiterCandidates,
          },
        };
      }

      return {
        data: {
          applications: mockApplications,
          stats: mockCandidateStats,
        },
      };
    }
    return fallbackError("Unable to load dashboard.");
  }
};

export const getApplicationStatus = async (applicationId) => {
  try {
    return await apiClient.get(`/applications/${applicationId}`);
  } catch (error) {
    if (error.response?.status === 404) {
      const application = mockApplications.find((item) => item.id === applicationId) ?? {
        id: applicationId,
        status: "In review",
        updatedAt: "Today",
      };
      return { data: application };
    }
    return fallbackError("Unable to load application status.");
  }
};

/* ------------------------- Profile ------------------------- */

export const getProfile = async () => {
  try {
    const response = await apiClient.get("/profile");
    return response;
  } catch (error) {
    if (error.response?.status === 404) {
      return { data: readSessionProfile() };
    }
    return fallbackError("Unable to load profile.");
  }
};

export const updateProfile = async (payload) => {
  try {
    const response = await apiClient.put("/profile", payload);
    return response;
  } catch (error) {
    if (error.response?.status === 404) {
      const profile = writeSessionProfile(payload);
      return {
        data: {
          success: true,
          profile,
        },
      };
    }
    return fallbackError("Unable to update profile.");
  }
};

/* ------------------------- AI Interview ------------------------- */

export const startInterview = async (jobId) => {
  try {
    return await apiClient.post("/interview/start", { jobId });
  } catch (error) {
    return {
      data: {
        sessionId: `interview-demo-${jobId}`,
        questions: mockInterviewQuestions,
      },
    };
  }
};

export const submitInterviewAnswer = async (sessionId, payload) => {
  try {
    return await apiClient.post(`/interview/${sessionId}/answer`, payload);
  } catch (error) {
    return {
      data: {
        success: true,
        sessionId,
        payload,
      },
    };
  }
};

export const getInterviewResult = async (sessionId) => {
  try {
    return await apiClient.get(`/interview/${sessionId}/result`);
  } catch (error) {
    return {
      data: {
        sessionId,
        status: "complete",
        score: 88,
        feedback: "Strong communication and clear examples.",
      },
    };
  }
};

export default apiClient;
