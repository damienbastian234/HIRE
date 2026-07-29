import { useCallback, useEffect, useState } from "react";
import { mockUser } from "../services/mockData";

// Lightweight mock auth hook. Once the backend is connected, replace the
// localStorage-based checks with real calls to services/api.js (login/register)
// and store the returned token instead of a mock flag.
export default function useAuth() {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("hire_session");
    if (stored) {
      setUser(JSON.parse(stored));
    }
    setIsLoading(false);
  }, []);

  const signIn = useCallback((role = "candidate") => {
    const session = role === "recruiter" ? { ...mockUser, role: "recruiter" } : mockUser;
    localStorage.setItem("hire_session", JSON.stringify(session));
    setUser(session);
    return session;
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem("hire_session");
    setUser(null);
  }, []);

  return { user, isLoading, signIn, signOut, isAuthenticated: Boolean(user) };
}
