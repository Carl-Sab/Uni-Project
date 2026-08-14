import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { GraduationCap, ArrowRight, Info } from "lucide-react";
import { useAuth } from "../lib/AuthContext";

const TEST_IDS = [
  { id: "S2023011", name: "Maya Haddad" },
  { id: "S2023027", name: "Jad Mansour" },
  { id: "S2024019", name: "Karim Nassar" },
  { id: "S2025008", name: "Rania Khoury" },
  { id: "S2026042", name: "Lynn Abou Chakra" },
];

export default function Login() {
  const [studentId, setStudentId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!studentId.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(studentId.trim());
      navigate("/portal");
    } catch {
      setError("We couldn't find a student with that ID. Double-check and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 px-4">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-sm"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/25">
            <GraduationCap className="size-6" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-ink-900">
            Eurisko University
          </h1>
          <p className="mt-1 text-sm text-ink-500">Sign in to your student portal</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-ink-100 bg-white p-6 shadow-sm shadow-ink-950/[0.03]"
        >
          <label htmlFor="student_id" className="mb-1.5 block text-sm font-medium text-ink-700">
            Student ID
          </label>
          <input
            id="student_id"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            placeholder="S2023011"
            autoFocus
            className="w-full rounded-xl border border-ink-200 px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-300 transition-colors duration-150 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />

          {error && (
            <motion.p
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-2 text-sm text-amber-500"
            >
              {error}
            </motion.p>
          )}

          <button
            type="submit"
            disabled={submitting || !studentId.trim()}
            className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-xl bg-brand-600 py-2.5 text-sm font-medium text-white shadow-sm transition-colors duration-150 hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Continue"}
            {!submitting && <ArrowRight className="size-4" />}
          </button>
        </form>

        <div className="mt-5 rounded-xl border border-dashed border-ink-200 bg-white/60 p-4">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-ink-500">
            <Info className="size-3.5" />
            Dev hint — test student IDs
          </div>
          <ul className="space-y-1">
            {TEST_IDS.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => setStudentId(s.id)}
                  className="flex w-full items-center justify-between rounded-lg px-2 py-1 text-left text-xs text-ink-500 transition-colors duration-150 hover:bg-brand-50 hover:text-brand-700"
                >
                  <span className="font-mono">{s.id}</span>
                  <span>{s.name}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </motion.div>
    </div>
  );
}
