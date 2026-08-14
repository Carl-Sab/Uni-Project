import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, TriangleAlert } from "lucide-react";
import { useEligibility } from "../../lib/queries";

export function EligibilityBadge({ courseCode }: { courseCode: string }) {
  // Fetched eagerly so the badge shows real eligibility at a glance -
  // hover only reveals the *reason*, it doesn't gate the check itself.
  const { data, isLoading } = useEligibility(courseCode, true);
  const [hovered, setHovered] = useState(false);

  const eligible = data?.eligible;
  const missing = data?.prerequisites.filter((p) => !p.satisfied) ?? [];

  if (isLoading) {
    return <span className="inline-block h-6 w-24 animate-shimmer rounded-full" />;
  }

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      tabIndex={0}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
    >
      <span
        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-colors duration-150 ${
          data === undefined
            ? "bg-ink-100 text-ink-500"
            : eligible
              ? "bg-good-100 text-good-500"
              : "bg-amber-100 text-amber-500"
        }`}
      >
        {data === undefined ? (
          "Unknown"
        ) : eligible ? (
          <>
            <Check className="size-3.5" /> Eligible
          </>
        ) : (
          <>
            <TriangleAlert className="size-3.5" /> Missing prereq
          </>
        )}
      </span>

      <AnimatePresence>
        {hovered && data && !eligible && missing.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full z-20 mt-2 w-56 rounded-xl border border-ink-100 bg-white p-3 text-left text-xs text-ink-700 shadow-lg"
          >
            <p className="mb-1 font-medium text-ink-900">Why not eligible</p>
            <ul className="space-y-1">
              {missing.map((p) => (
                <li key={p.prerequisite_course_code}>
                  <span className="font-medium">{p.prerequisite_course_code}</span>
                  {p.grade_earned
                    ? ` — earned ${p.grade_earned}, needs C- or above`
                    : " — not yet completed"}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}
