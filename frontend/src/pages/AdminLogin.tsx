import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useAdminAuth } from "../lib/AdminAuthContext";

export default function AdminLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAdminAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate("/admin");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-steel-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="mb-3 flex size-11 items-center justify-center rounded-lg bg-steel-700 text-steel-50">
            <ShieldCheck className="size-5" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-steel-50">Admin Panel</h1>
          <p className="mt-1 text-sm text-steel-400">Eurisko University</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-steel-800 bg-steel-900 p-6"
        >
          <label htmlFor="username" className="mb-1.5 block text-xs font-medium text-steel-300">
            Username
          </label>
          <input
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            className="mb-4 w-full rounded-md border border-steel-700 bg-steel-950 px-3 py-2 text-sm text-steel-50 placeholder:text-steel-600 transition-colors duration-100 focus:border-steel-400 focus:outline-none"
          />

          <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-steel-300">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-steel-700 bg-steel-950 px-3 py-2 text-sm text-steel-50 placeholder:text-steel-600 transition-colors duration-100 focus:border-steel-400 focus:outline-none"
          />

          {error && <p className="mt-3 text-sm text-amber-400">{error}</p>}

          <button
            type="submit"
            disabled={submitting || !username.trim() || !password}
            className="mt-5 w-full rounded-md bg-steel-600 py-2.5 text-sm font-medium text-white transition-colors duration-100 hover:bg-steel-500 disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
