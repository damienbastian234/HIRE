import { Outlet } from "react-router-dom";
import { FiGrid, FiBriefcase, FiUser, FiUpload } from "react-icons/fi";
import Navbar from "../components/Navbar";
import Sidebar from "../components/Sidebar";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Overview", icon: <FiGrid size={16} /> },
  { to: "/jobs", label: "Jobs", icon: <FiBriefcase size={16} /> },
  { to: "/resume-upload", label: "Resume", icon: <FiUpload size={16} /> },
  { to: "/profile", label: "Profile", icon: <FiUser size={16} /> },
];

export default function DashboardLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="container-page flex flex-1 gap-8">
        <Sidebar items={NAV_ITEMS} />
        <main className="min-w-0 flex-1 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
