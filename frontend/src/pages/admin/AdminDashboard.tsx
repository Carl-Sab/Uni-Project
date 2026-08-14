import { Users, BookOpen, ListChecks, FileText, Layers, Clock } from "lucide-react";
import { useAdminStats } from "../../lib/adminQueries";
import { AdminCard } from "../../components/admin/ui";

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function AdminDashboard() {
  const { data: stats, isLoading } = useAdminStats();

  const tiles = [
    { label: "Students", value: stats?.student_count, icon: Users },
    { label: "Courses", value: stats?.course_count, icon: BookOpen },
    { label: "Enrollments", value: stats?.enrollment_count, icon: ListChecks },
    { label: "Indexed documents", value: stats?.indexed_document_count, icon: FileText },
    { label: "Total chunks", value: stats?.total_chunk_count, icon: Layers },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-steel-900">Dashboard</h1>
        <p className="mt-0.5 text-sm text-steel-500">System overview.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {tiles.map(({ label, value, icon: Icon }) => (
          <AdminCard key={label} className="p-4">
            <div className="mb-2 flex items-center gap-2 text-steel-400">
              <Icon className="size-3.5" />
              <span className="text-xs font-medium">{label}</span>
            </div>
            <p className="text-2xl font-semibold tabular-nums text-steel-900">
              {isLoading ? (
                <span className="inline-block h-7 w-10 animate-pulse rounded bg-steel-100" />
              ) : (
                value
              )}
            </p>
          </AdminCard>
        ))}
      </div>

      <AdminCard className="p-4">
        <div className="flex items-center gap-2 text-steel-500">
          <Clock className="size-4" />
          <span className="text-sm">
            Last ingestion:{" "}
            <span className="font-medium text-steel-900">
              {isLoading ? "…" : formatDate(stats?.last_ingested_at ?? null)}
            </span>
          </span>
        </div>
      </AdminCard>
    </div>
  );
}
