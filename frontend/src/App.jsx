import { Routes, Route } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import DashboardLayout from "./layouts/DashboardLayout";

import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import CandidateDashboard from "./pages/CandidateDashboard";
import RecruiterDashboard from "./pages/RecruiterDashboard";
import ResumeUploadPage from "./pages/ResumeUploadPage";
import AIInterviewPage from "./pages/AIInterviewPage";
import ProfilePage from "./pages/ProfilePage";
import JobListingsPage from "./pages/JobListingsPage";
import JobDetailsPage from "./pages/JobDetailsPage";
import ApplicationStatusPage from "./pages/ApplicationStatusPage";
import NotFoundPage from "./pages/NotFoundPage";
import useAuth from "./hooks/useAuth";

export default function App() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/jobs" element={<JobListingsPage />} />
        <Route path="/jobs/:jobId" element={<JobDetailsPage />} />
        <Route path="/interview" element={<AIInterviewPage />} />
        <Route path="/application-status" element={<ApplicationStatusPage />} />
      </Route>

      <Route element={<DashboardLayout />}>
        <Route
          path="/dashboard"
          element={user?.role === "recruiter" ? <RecruiterDashboard /> : <CandidateDashboard />}
        />
        <Route path="/resume-upload" element={<ResumeUploadPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
