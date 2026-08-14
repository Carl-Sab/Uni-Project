import { motion } from "framer-motion";
import { Check, Clock, MessageCircleQuestion } from "lucide-react";
import { useAppointments, useApproveAppointment } from "../../lib/queries";
import { Card } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/Skeleton";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-500",
  approved: "bg-good-100 text-good-500",
  declined: "bg-ink-100 text-ink-500",
};

export default function Appointments() {
  const { data: appointments, isLoading } = useAppointments();
  const approve = useApproveAppointment();

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const hasAny = (appointments?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink-900">Advisor Appointments</h1>
        <p className="mt-1 text-sm text-ink-500">
          Proposed by the assistant, confirmed by you — nothing is booked without approval.
        </p>
      </div>

      {!hasAny ? (
        <EmptyState
          icon={<MessageCircleQuestion className="size-5" />}
          title="No appointments yet"
          hint='Ask the assistant to set one up — e.g. "I want to talk to my advisor about my capstone project."'
        />
      ) : (
        <div className="space-y-3">
          {appointments!.map((a, i) => (
            <Card key={a.id} className="p-5" delay={i * 0.06}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-ink-900">{a.reason}</p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-500">
                    <Clock className="size-3.5" /> {a.preferred_time}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium capitalize ${STATUS_STYLE[a.status]}`}
                >
                  {a.status}
                </span>
              </div>

              {a.status === "pending" && (
                <motion.button
                  whileTap={{ scale: 0.96 }}
                  onClick={() => approve.mutate(a.id)}
                  disabled={approve.isPending}
                  className="mt-4 flex items-center gap-1.5 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors duration-150 hover:bg-brand-700 disabled:opacity-60"
                >
                  <Check className="size-4" />
                  {approve.isPending ? "Confirming…" : "Confirm appointment"}
                </motion.button>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
