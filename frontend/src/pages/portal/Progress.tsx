import { Target } from "lucide-react";
import { useDegreeProgress } from "../../lib/queries";
import { Card } from "../../components/ui/Card";
import { ProgressBar } from "../../components/ui/ProgressBar";
import { SkeletonCard } from "../../components/ui/Skeleton";

export default function Progress() {
  const { data: categories, isLoading } = useDegreeProgress();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Degree Progress</h1>
        <p className="mt-1 text-sm text-ink-500">
          Every requirement category must be individually satisfied — surplus credits in one
          don't offset a shortfall in another.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {categories!.map((cat, i) => {
          const earnedPct = cat.credits_required
            ? (cat.credits_earned / cat.credits_required) * 100
            : 0;
          const inProgressPct = cat.credits_required
            ? (cat.credits_in_progress / cat.credits_required) * 100
            : 0;
          const complete = cat.credits_earned >= cat.credits_required;

          return (
            <Card key={cat.category_id} className="p-5" delay={i * 0.07}>
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`flex size-8 items-center justify-center rounded-lg ${
                      complete ? "bg-good-100 text-good-500" : "bg-brand-50 text-brand-600"
                    }`}
                  >
                    <Target className="size-4" />
                  </div>
                  <h2 className="text-sm font-semibold text-ink-900">{cat.category_name}</h2>
                </div>
                {complete && (
                  <span className="rounded-full bg-good-100 px-2 py-0.5 text-[11px] font-medium text-good-500">
                    Complete
                  </span>
                )}
              </div>

              <ProgressBar earnedPct={earnedPct} inProgressPct={inProgressPct} />

              <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-500">
                <span>
                  <strong className="text-ink-900">{cat.credits_earned}</strong> earned
                </span>
                {cat.credits_in_progress > 0 && (
                  <span>
                    <strong className="text-brand-600">{cat.credits_in_progress}</strong> in progress
                  </span>
                )}
                <span>
                  <strong className="text-ink-900">{cat.credits_remaining}</strong> remaining
                </span>
                <span>of {cat.credits_required} required</span>
              </div>

              {cat.eligible_courses_not_taken.length > 0 && (
                <div className="mt-3 border-t border-ink-50 pt-3">
                  <p className="mb-1.5 text-xs font-medium text-ink-500">Could fill this gap</p>
                  <div className="flex flex-wrap gap-1.5">
                    {cat.eligible_courses_not_taken.map((c) => (
                      <span
                        key={c.course_code}
                        className="rounded-lg bg-ink-50 px-2 py-1 text-xs font-medium text-ink-700"
                        title={c.title}
                      >
                        {c.course_code}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
