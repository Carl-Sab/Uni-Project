import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "./api";
import { onUnauthorized, setToken } from "./tokenStore";

const STORAGE_KEY = "eurisko.student_id";

interface AuthState {
  studentId: string | null;
  loading: boolean;
  error: string | null;
  login: (studentId: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

async function doLogin(studentId: string): Promise<void> {
  const res = await api.post<{ access_token: string }>("/api/auth/student/login", {
    student_id: studentId,
  });
  setToken(res.access_token);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [studentId, setStudentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = onUnauthorized(() => {
      setToken(null);
      setStudentId(null);
      sessionStorage.removeItem(STORAGE_KEY);
    });

    const remembered = sessionStorage.getItem(STORAGE_KEY);
    if (!remembered) {
      setLoading(false);
      return unsubscribe;
    }
    doLogin(remembered)
      .then(() => setStudentId(remembered))
      .catch(() => sessionStorage.removeItem(STORAGE_KEY))
      .finally(() => setLoading(false));

    return unsubscribe;
  }, []);

  async function login(id: string) {
    setError(null);
    try {
      await doLogin(id);
      sessionStorage.setItem(STORAGE_KEY, id);
      setStudentId(id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
      throw e;
    }
  }

  function logout() {
    setToken(null);
    setStudentId(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }

  return (
    <AuthContext.Provider value={{ studentId, loading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
