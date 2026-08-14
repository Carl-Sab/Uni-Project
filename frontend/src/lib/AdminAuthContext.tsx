import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "./api";
import { onUnauthorized, setToken } from "./tokenStore";

interface AdminAuthState {
  username: string | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AdminAuthContext = createContext<AdminAuthState | null>(null);

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  // No silent reload-refresh here, unlike the student side: admin login
  // needs a password we never persist anywhere (not even sessionStorage),
  // so a reload always lands back at /admin/login - the in-memory-only JWT
  // is the point, not an inconvenience to work around.
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return onUnauthorized(() => {
      setToken(null);
      setUsername(null);
    });
  }, []);

  async function login(usernameInput: string, password: string) {
    setError(null);
    setLoading(true);
    try {
      const res = await api.post<{ access_token: string }>("/api/auth/admin/login", {
        username: usernameInput,
        password,
      });
      setToken(res.access_token);
      setUsername(usernameInput);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
      throw e;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setToken(null);
    setUsername(null);
  }

  return (
    <AdminAuthContext.Provider value={{ username, loading, error, login, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth(): AdminAuthState {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error("useAdminAuth must be used within AdminAuthProvider");
  return ctx;
}
