import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";

export default function Home() {
  const { studentId, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={studentId ? "/portal" : "/login"} replace />;
}
