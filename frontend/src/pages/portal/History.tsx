import { motion } from "framer-motion";
import { BookX } from "lucide-react";
import { useCourseHistory, useProfile } from "../../lib/queries";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { StatCounter } from "../../components/ui/StatCounter";

const STATUS_STYLE: Record<string, string> = {
  Completed: "text-ink-500",
  "In progress": "text-brand-600",
};

export default function History() {
  const { data: terms, isLoading } = useCourseHistory();
  const { data: profile } = useProfile();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const hasHistory = (terms?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Academic History</h1>
          <p className="mt-1 text-sm text-ink-500">Every course, term by term.</p>
        </div>
        <div className="rounded-2xl border border-ink-100 bg-white px-5 py-3 text-right">
          <p className="text-xs font-medium text-ink-500">Cumulative GPA</p>
          <p className="text-xl font-semibold text-ink-900">
            {profile?.cumulative_gpa ? (
              <StatCounter value={parseFloat(profile.cumulative_gpa)} decimals={2} />
            ) : (
              <span className="text-sm text-ink-300">N/A</span>
            )}
          </p>
        </div>
      </div>

      {!hasHistory ? (
        <EmptyState
          icon={<BookX className="size-5" />}
          title="No academic history yet"
          hint="This is your first term — completed courses and grades will show up here once your first term wraps up."
        />
      ) : (
        <div className="space-y-4">
          {terms!.map((term, ti) => (
            <Card key={term.term_code} className="p-5" delay={ti * 0.06}>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-ink-900">{term.term_name}</h2>
                <span className="rounded-lg bg-ink-50 px-2.5 py-1 text-xs font-medium text-ink-700">
                  Term GPA: {term.term_gpa ?? "N/A"}
                </span>
              </div>
              <div className="divide-y divide-ink-50">
                {term.courses.map((c, i) => (
                  <motion.div
                    key={c.course_code}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.2, delay: ti * 0.06 + i * 0.03 }}
                    className="flex items-center justify-between rounded-lg px-2 py-2.5 transition-colors duration-150 hover:bg-ink-50"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink-900">
                        {c.course_code} · {c.title}
                      </p>
                      <p className={`text-xs ${STATUS_STYLE[c.status] ?? "text-ink-500"}`}>
                        {c.status} · {c.credits} credits
                      </p>
                    </div>
                    <span
                      className={`min-w-9 rounded-lg px-2 py-1 text-center text-sm font-semibold ${
                        c.grade === "F"
                          ? "bg-amber-100 text-amber-500"
                          : c.grade
                            ? "bg-good-100 text-good-500"
                            : "bg-ink-100 text-ink-500"
                      }`}
                    >
                      {c.grade ?? "—"}
                    </span>
                  </motion.div>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
