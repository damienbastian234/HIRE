import { useCallback, useEffect, useState } from "react";

const SESSION_KEY = "hire_session";
const TOKEN_KEY = "hire_token";

function readStoredSession() {
  try {
    const stored = localStorage.getItem(SESSION_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

function persistSession(session, token = null) {
  if (session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    }
  } else {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(TOKEN_KEY);
  }
}

const store = {
  user: readStoredSession(),
  listeners: new Set(),
};

function emitAuthChange(nextUser) {
  store.user = nextUser;
  store.listeners.forEach((listener) => listener(nextUser));
  window.dispatchEvent(new CustomEvent("hire-auth", { detail: nextUser }));
}

export default function useAuth() {
  const [user, setUser] = useState(store.user);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const listener = (nextUser) => {
      setUser(nextUser);
    };
    store.listeners.add(listener);
    setUser(store.user);
    setIsLoading(false);

    const handleStorage = (event) => {
      if (event.key === SESSION_KEY) {
        const nextUser = readStoredSession();
        emitAuthChange(nextUser);
      }
    };

    const handleAuthEvent = (event) => {
      const newUser = event.detail ?? null;
      setUser(newUser);
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener("hire-auth", handleAuthEvent, { once: false });

    return () => {
      store.listeners.delete(listener);
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("hire-auth", handleAuthEvent);
    };
  }, []);

  const signIn = useCallback((authUser, token = null) => {
    const session = authUser ? { ...authUser } : null;
    persistSession(session, token);
    emitAuthChange(session);
    return session;
  }, []);

  const signOut = useCallback(() => {
    persistSession(null);
    emitAuthChange(null);
  }, []);

  const updateSessionUser = useCallback((nextUser) => {
    const current = store.user || readStoredSession();
    const merged = { ...(current || {}), ...(nextUser || {}) };
    persistSession(merged);
    emitAuthChange(merged);
  }, []);

  return { user, isLoading, signIn, signOut, updateSessionUser, isAuthenticated: Boolean(user) };
}
