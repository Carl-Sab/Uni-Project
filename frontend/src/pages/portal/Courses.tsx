import { useState } from "react";
import { motion } from "framer-motion";
import { Search } from "lucide-react";
import { useCatalogue } from "../../lib/queries";
import { Card } from "../../components/ui/Card";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { EligibilityBadge } from "../../components/ui/EligibilityBadge";

export default function Courses() {
  const { data: courses, isLoading } = useCatalogue();
  const [query, setQuery] = useState("");

  const filtered = (courses ?? []).filter(
    (c) =>
      c.course_code.toLowerCase().includes(query.toLowerCase()) ||
      c.title.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Course Catalogue</h1>
          <p className="mt-1 text-sm text-ink-500">
            Hover a badge to see why a course isn't eligible yet.
          </p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-300" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search courses…"
            className="w-56 rounded-xl border border-ink-200 py-2 pl-9 pr-3 text-sm text-ink-900 placeholder:text-ink-300 transition-colors duration-150 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <Card className="overflow-hidden">
          <div className="divide-y divide-ink-50">
            {filtered.map((c, i) => (
              <motion.div
                key={c.course_code}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: Math.min(i * 0.02, 0.4) }}
                className="flex items-start justify-between gap-4 px-5 py-4 transition-colors duration-150 hover:bg-brand-50/30"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink-900">
                    {c.course_code} · {c.title}{" "}
                    <span className="font-normal text-ink-400">({c.credits} cr)</span>
                  </p>
                  <p className="mt-1 line-clamp-2 text-sm text-ink-500">{c.description}</p>
                  {c.prerequisites.length > 0 && (
                    <p className="mt-1.5 text-xs text-ink-400">
                      Prerequisites:{" "}
                      <span className="font-medium text-ink-500">
                        {c.prerequisites.join(", ")}
                      </span>
                    </p>
                  )}
                </div>
                <div className="shrink-0 pt-0.5">
                  <EligibilityBadge courseCode={c.course_code} />
                </div>
              </motion.div>
            ))}
            {filtered.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-ink-500">
                No courses match “{query}”.
              </p>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
