import { useState } from "react";
import { motion } from "framer-motion";
import { CalendarClock, Check, X } from "lucide-react";
import { useApproveAppointment } from "../../lib/queries";

interface Proposal {
  appointment_id: number;
  status: string;
  reason: string;
  preferred_time: string;
}

export function AppointmentCard({ proposal }: { proposal: Proposal }) {
  const [state, setState] = useState<"pending" | "approved" | "cancelled">(
    proposal.status === "approved" ? "approved" : "pending"
  );
  const approve = useApproveAppointment();

  async function confirm() {
    await approve.mutateAsync(proposal.appointment_id);
    setState("approved");
  }

  return (
    <div className="mt-2 w-full max-w-sm rounded-2xl border border-brand-200 bg-brand-50/60 p-4">
      <div className="mb-2 flex items-center gap-2 text-brand-700">
        <CalendarClock className="size-4" />
        <span className="text-xs font-semibold uppercase tracking-wide">
          Advisor appointment proposal
        </span>
      </div>
      <p className="text-sm text-ink-900">{proposal.reason}</p>
      <p className="mt-0.5 text-sm text-ink-500">{proposal.preferred_time}</p>

      {state === "pending" && (
        <div className="mt-3 flex gap-2">
          <motion.button
            whileTap={{ scale: 0.94 }}
            onClick={confirm}
            disabled={approve.isPending}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-brand-600 py-2 text-sm font-medium text-white shadow-sm transition-colors duration-150 hover:bg-brand-700 disabled:opacity-60"
          >
            <Check className="size-4" />
            {approve.isPending ? "Confirming…" : "Confirm"}
          </motion.button>
          <button
            onClick={() => setState("cancelled")}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-ink-200 py-2 text-sm font-medium text-ink-500 transition-colors duration-150 hover:bg-ink-50"
          >
            <X className="size-4" />
            Cancel
          </button>
        </div>
      )}
      {state === "approved" && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 20 }}
          className="mt-3 flex items-center gap-1.5 rounded-xl bg-good-100 px-3 py-2 text-sm font-medium text-good-500"
        >
          <Check className="size-4" /> Confirmed and booked
        </motion.div>
      )}
      {state === "cancelled" && (
        <div className="mt-3 rounded-xl bg-ink-100 px-3 py-2 text-sm font-medium text-ink-500">
          Proposal cancelled
        </div>
      )}
    </div>
  );
}
