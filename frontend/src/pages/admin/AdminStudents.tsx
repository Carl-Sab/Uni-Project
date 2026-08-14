import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useAdminStudents } from "../../lib/adminQueries";
import { AdminCard, StatusPill } from "../../components/admin/ui";
import type { AdminStudentSummary } from "../../lib/adminTypes";

type SortKey = keyof Pick<
  AdminStudentSummary,
  "student_id" | "first_name" | "program_name" | "academic_status" | "cumulative_gpa" | "total_credits_earned"
>;

export default function AdminStudents() {
  const { data: students, isLoading } = useAdminStudents();
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>("student_id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sorted = useMemo(() => {
    if (!students) return [];
    const copy = [...students];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const an = av === null ? -Infinity : av;
      const bn = bv === null ? -Infinity : bv;
      if (an < bn) return sortDir === "asc" ? -1 : 1;
      if (an > bn) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return copy;
  }, [students, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function SortHeader({ label, sortKeyValue }: { label: string; sortKeyValue: SortKey }) {
    const active = sortKey === sortKeyValue;
    return (
      <th
        onClick={() => toggleSort(sortKeyValue)}
        className="cursor-pointer select-none px-4 py-2.5 hover:text-steel-700"
      >
        <span className="flex items-center gap-1">
          {label}
          {active && (sortDir === "asc" ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
        </span>
      </th>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-steel-900">Students</h1>
        <p className="mt-0.5 text-sm text-steel-500">{students?.length ?? 0} students enrolled.</p>
      </div>

      <AdminCard className="overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-steel-100 bg-steel-50 text-xs font-medium text-steel-500">
            <tr>
              <SortHeader label="Student ID" sortKeyValue="student_id" />
              <SortHeader label="Name" sortKeyValue="first_name" />
              <SortHeader label="Programme" sortKeyValue="program_name" />
              <SortHeader label="Standing" sortKeyValue="academic_status" />
              <SortHeader label="GPA" sortKeyValue="cumulative_gpa" />
              <SortHeader label="Credits" sortKeyValue="total_credits_earned" />
            </tr>
          </thead>
          <tbody className="divide-y divide-steel-50">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-steel-400">
                  Loading…
                </td>
              </tr>
            ) : (
              sorted.map((s) => (
                <tr
                  key={s.student_id}
                  onClick={() => navigate(`/admin/students/${s.student_id}`)}
                  className="cursor-pointer transition-colors duration-100 hover:bg-steel-50"
                >
                  <td className="px-4 py-2.5 font-mono text-xs text-steel-600">{s.student_id}</td>
                  <td className="px-4 py-2.5 font-medium text-steel-800">
                    {s.first_name} {s.last_name}
                  </td>
                  <td className="px-4 py-2.5 text-steel-500">{s.program_name}</td>
                  <td className="px-4 py-2.5">
                    <StatusPill status={s.academic_status} />
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-steel-700">
                    {s.cumulative_gpa ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-steel-700">{s.total_credits_earned}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </AdminCard>
    </div>
  );
}
