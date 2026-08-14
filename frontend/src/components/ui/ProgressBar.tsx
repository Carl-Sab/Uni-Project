import { motion } from "framer-motion";

export function ProgressBar({
  earnedPct,
  inProgressPct,
  size = "md",
}: {
  earnedPct: number;
  inProgressPct?: number;
  size?: "sm" | "md";
}) {
  const height = size === "sm" ? "h-1.5" : "h-2.5";
  return (
    <div className={`w-full ${height} rounded-full bg-ink-100 overflow-hidden relative`}>
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full bg-brand-600"
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(earnedPct, 100)}%` }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      />
      {inProgressPct ? (
        <motion.div
          className="absolute inset-y-0 rounded-full bg-brand-300"
          style={{ left: `${Math.min(earnedPct, 100)}%` }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(inProgressPct, 100 - earnedPct)}%` }}
          transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
        />
      ) : null}
    </div>
  );
}
