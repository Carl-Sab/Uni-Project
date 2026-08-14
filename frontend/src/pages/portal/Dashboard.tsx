import { motion } from "framer-motion";
import { Award, BookOpen, CalendarClock, TrendingUp } from "lucide-react";
import { useProfile, useDegreeProgress, useSchedule } from "../../lib/queries";
import { Card } from "../../components/ui/Card";
import { ProgressBar } from "../../components/ui/ProgressBar";
import { StatCounter } from "../../components/ui/StatCounter";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { EmptyState } from "../../components/ui/EmptyState";

const TODAY = new Date().toLocaleDateString("en-US", { weekday: "short" });

export default function Dashboard() {
  const { data: profile, isLoading: loadingProfile } = useProfile();
  const { data: progress, isLoading: loadingProgress } = useDegreeProgress();
  const { data: schedule, isLoading: loadingSchedule } = useSchedule();

  const totalRequired = progress?.reduce((s, c) => s + c.credits_required, 0) ?? 0;
  const totalEarned = progress?.reduce((s, c) => s + c.credits_earned, 0) ?? 0;
  const totalInProgress = progress?.reduce((s, c) => s + c.credits_in_progress, 0) ?? 0;
  const earnedPct = totalRequired ? (totalEarned / totalRequired) * 100 : 0;
  const inProgressPct = totalRequired ? (totalInProgress / totalRequired) * 100 : 0;

  const todayClasses = (schedule ?? [])
    .filter((s) => s.days.includes(TODAY))
    .sort((a, b) => a.start_time.localeCompare(b.start_time));

  if (loadingProfile || loadingProgress) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">
          Welcome back, {profile?.first_name}
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          {profile?.program_name} · {profile?.academic_status}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Card className="p-5" delay={0}>
          <div className="mb-3 flex items-center gap-2 text-ink-500">
            <TrendingUp className="size-4" />
            <span className="text-sm font-medium">Cumulative GPA</span>
          </div>
          <p className="text-3xl font-semibold tracking-tight text-ink-900">
            {profile?.cumulative_gpa ? (
              <StatCounter value={parseFloat(profile.cumulative_gpa)} decimals={2} />
            ) : (
              <span className="text-xl text-ink-300">Not yet available</span>
            )}
          </p>
        </Card>

        <Card className="p-5" delay={0.05}>
          <div className="mb-3 flex items-center gap-2 text-ink-500">
            <Award className="size-4" />
            <span className="text-sm font-medium">Credits Earned</span>
          </div>
          <p className="text-3xl font-semibold tracking-tight text-ink-900">
            <StatCounter value={profile?.total_credits_earned ?? 0} />
            <span className="ml-1 text-base font-normal text-ink-300">/ {totalRequired}</span>
          </p>
        </Card>

        <Card className="p-5" delay={0.1}>
          <div className="mb-3 flex items-center gap-2 text-ink-500">
            <BookOpen className="size-4" />
            <span className="text-sm font-medium">Advisor</span>
          </div>
          <p className="text-lg font-medium text-ink-900">{profile?.advisor_name}</p>
          <p className="mt-0.5 text-sm text-ink-500">Expected: {profile?.expected_graduation_term}</p>
        </Card>
      </div>

      <Card className="p-5" delay={0.15}>
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-medium text-ink-700">Overall degree progress</span>
          <span className="text-sm text-ink-500">
            {totalEarned} / {totalRequired} credits
          </span>
        </div>
        <ProgressBar earnedPct={earnedPct} inProgressPct={inProgressPct} />
        <div className="mt-2 flex gap-4 text-xs text-ink-500">
          <span className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-brand-600" /> Earned
          </span>
          {totalInProgress > 0 && (
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-brand-300" /> In progress
            </span>
          )}
        </div>
      </Card>

      <Card className="p-5" delay={0.2}>
        <div className="mb-4 flex items-center gap-2">
          <CalendarClock className="size-4 text-ink-500" />
          <span className="text-sm font-medium text-ink-700">Today's classes</span>
        </div>

        {loadingSchedule ? (
          <div className="space-y-2">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-14 animate-shimmer rounded-xl" />
            ))}
          </div>
        ) : todayClasses.length === 0 ? (
          <p className="text-sm text-ink-500">No classes scheduled for today.</p>
        ) : (
          <div className="space-y-2">
            {todayClasses.map((c, i) => (
              <motion.div
                key={c.course_code}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.22, delay: 0.05 * i }}
                className="flex items-center justify-between rounded-xl border border-ink-100 px-3.5 py-3 transition-colors duration-150 hover:border-brand-200 hover:bg-brand-50/40"
              >
                <div>
                  <p className="text-sm font-medium text-ink-900">
                    {c.course_code} · {c.title}
                  </p>
                  <p className="text-xs text-ink-500">
                    {c.room} · {c.instructor}
                  </p>
                </div>
                <span className="text-sm font-medium text-brand-600">
                  {c.start_time.slice(0, 5)}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </Card>

      {totalEarned === 0 && (
        <EmptyState
          icon={<Award className="size-5" />}
          title="Your journey starts here"
          hint="You haven't completed any courses yet — once your first term's grades are posted, your GPA and progress will appear here."
        />
      )}
    </div>
  );
}
