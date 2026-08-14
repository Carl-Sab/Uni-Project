import { motion, AnimatePresence } from "framer-motion";
import { FileSearch, Search } from "lucide-react";
import type { ToolActivity as ToolActivityT } from "../../lib/useChatStream";

const LABELS: Record<string, string> = {
  search_documents: "Searching documents",
  get_my_schedule: "Checking your schedule",
  get_my_courses: "Checking your courses",
  get_my_degree_progress: "Checking your degree progress",
  check_course_eligibility: "Checking eligibility",
  request_advisor_appointment: "Proposing an appointment",
};

export function ToolActivityList({ calls }: { calls: ToolActivityT[] }) {
  const running = calls.filter((c) => c.status === "running");
  if (running.length === 0) return null;

  return (
    <AnimatePresence>
      <div className="mb-2 flex flex-col gap-1.5">
        {running.map((c, i) => (
          <motion.div
            key={c.tool + i}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-sm text-brand-600"
          >
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-pulse-dot rounded-full bg-brand-500" />
              <span className="relative inline-flex size-2 rounded-full bg-brand-600" />
            </span>
            {c.tool === "search_documents" ? (
              <FileSearch className="size-3.5" />
            ) : (
              <Search className="size-3.5" />
            )}
            <span>{LABELS[c.tool] ?? c.tool}…</span>
          </motion.div>
        ))}
      </div>
    </AnimatePresence>
  );
}
