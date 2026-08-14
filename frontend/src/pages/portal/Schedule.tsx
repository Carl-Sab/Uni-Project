import { motion } from "framer-motion";
import { CalendarX2, MapPin, User } from "lucide-react";
import { useSchedule } from "../../lib/queries";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/Skeleton";

const DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const DAY_NAMES: Record<string, string> = {
  Mon: "Monday",
  Tue: "Tuesday",
  Wed: "Wednesday",
  Thu: "Thursday",
  Fri: "Friday",
};

export default function Schedule() {
  const { data, isLoading } = useSchedule();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const byDay = new Map<string, NonNullable<typeof data>>();
  for (const day of DAY_ORDER) byDay.set(day, []);
  for (const item of data ?? []) {
    for (const day of DAY_ORDER) {
      if (item.days.includes(day)) byDay.get(day)!.push(item);
    }
  }
  for (const list of byDay.values()) list.sort((a, b) => a.start_time.localeCompare(b.start_time));

  const hasAny = (data?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Fall 2026 Schedule</h1>
        <p className="mt-1 text-sm text-ink-500">Your class times, rooms, and instructors.</p>
      </div>

      {!hasAny ? (
        <EmptyState
          icon={<CalendarX2 className="size-5" />}
          title="No classes this term"
          hint="You're not currently enrolled in any Fall 2026 classes."
        />
      ) : (
        <div className="space-y-5">
          {DAY_ORDER.filter((d) => (byDay.get(d)?.length ?? 0) > 0).map((day, dayIdx) => (
            <Card key={day} className="p-5" delay={dayIdx * 0.06}>
              <h2 className="mb-3 text-sm font-semibold text-brand-700">{DAY_NAMES[day]}</h2>
              <div className="space-y-2">
                {byDay.get(day)!.map((c, i) => (
                  <motion.div
                    key={c.course_code + day}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2, delay: dayIdx * 0.06 + i * 0.04 }}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-ink-100 px-4 py-3 transition-colors duration-150 hover:border-brand-200 hover:bg-brand-50/40"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink-900">
                        {c.course_code} · {c.title}
                      </p>
                      <div className="mt-1 flex items-center gap-3 text-xs text-ink-500">
                        <span className="flex items-center gap-1">
                          <MapPin className="size-3" /> {c.room}
                        </span>
                        <span className="flex items-center gap-1">
                          <User className="size-3" /> {c.instructor}
                        </span>
                      </div>
                    </div>
                    <span className="rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
                      {c.start_time.slice(0, 5)}–{c.end_time.slice(0, 5)}
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
