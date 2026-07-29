import axios from "axios";

// Base Axios instance. Swap VITE_API_BASE_URL in .env once the backend is live.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
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

export const login = (credentials) => {
  // credentials: { email, password }
  return apiClient.post("/auth/login", credentials);
};

export const register = (payload) => {
  // payload: { name, email, password, role }
  return apiClient.post("/auth/register", payload);
};

export const logout = () => {
  localStorage.removeItem("hire_token");
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

export const getJobs = (params) => {
  // params: { search, location, type, page }
  return apiClient.get("/jobs", { params });
};

export const getJobById = (jobId) => {
  return apiClient.get(`/jobs/${jobId}`);
};

export const applyJob = (jobId, payload) => {
  return apiClient.post(`/jobs/${jobId}/apply`, payload);
};

/* ------------------------- Dashboard ------------------------- */

export const getDashboard = (role) => {
  // role: "candidate" | "recruiter"
  return apiClient.get(`/dashboard/${role}`);
};

export const getApplicationStatus = (applicationId) => {
  return apiClient.get(`/applications/${applicationId}`);
};

/* ------------------------- Profile ------------------------- */

export const getProfile = () => {
  return apiClient.get("/profile");
};

export const updateProfile = (payload) => {
  return apiClient.put("/profile", payload);
};

/* ------------------------- AI Interview ------------------------- */

export const startInterview = (jobId) => {
  return apiClient.post("/interview/start", { jobId });
};

export const submitInterviewAnswer = (sessionId, payload) => {
  // payload: { questionId, answerText | answerAudioUrl }
  return apiClient.post(`/interview/${sessionId}/answer`, payload);
};

export const getInterviewResult = (sessionId) => {
  return apiClient.get(`/interview/${sessionId}/result`);
};

export default apiClient;
