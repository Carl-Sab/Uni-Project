import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useAdminEnrollments, useAdminStudents } from "../../lib/adminQueries";
import { AdminCard } from "../../components/admin/ui";

const PAGE_SIZE = 20;

export default function AdminEnrollments() {
  const [studentId, setStudentId] = useState("");
  const [termCode, setTermCode] = useState("");
  const [page, setPage] = useState(1);

  const { data: students } = useAdminStudents();
  const { data, isLoading } = useAdminEnrollments({
    studentId: studentId || undefined,
    termCode: termCode || undefined,
    page,
    pageSize: PAGE_SIZE,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-steel-900">Enrollments</h1>
        <p className="mt-0.5 text-sm text-steel-500">{data?.total ?? 0} total enrollments.</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={studentId}
          onChange={(e) => {
            setStudentId(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-steel-200 px-3 py-1.5 text-sm text-steel-700 focus:border-steel-400 focus:outline-none"
        >
          <option value="">All students</option>
          {students?.map((s) => (
            <option key={s.student_id} value={s.student_id}>
              {s.student_id} — {s.first_name} {s.last_name}
            </option>
          ))}
        </select>

        <input
          value={termCode}
          onChange={(e) => {
            setTermCode(e.target.value.toUpperCase());
            setPage(1);
          }}
          placeholder="Term, e.g. FA2026"
          className="w-44 rounded-md border border-steel-200 px-3 py-1.5 text-sm text-steel-700 placeholder:text-steel-400 focus:border-steel-400 focus:outline-none"
        />
      </div>

      <AdminCard className="overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-steel-100 bg-steel-50 text-xs font-medium text-steel-500">
            <tr>
              <th className="px-4 py-2.5">Student</th>
              <th className="px-4 py-2.5">Term</th>
              <th className="px-4 py-2.5">Course</th>
              <th className="px-4 py-2.5">Credits</th>
              <th className="px-4 py-2.5">Grade</th>
              <th className="px-4 py-2.5">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-steel-50">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-steel-400">
                  Loading…
                </td>
              </tr>
            ) : data && data.items.length > 0 ? (
              data.items.map((e, i) => (
                <tr key={`${e.student_id}-${e.term_code}-${e.course_code}-${i}`} className="hover:bg-steel-50/60">
                  <td className="px-4 py-2 text-steel-700">
                    {e.student_name}{" "}
                    <span className="font-mono text-xs text-steel-400">({e.student_id})</span>
                  </td>
                  <td className="px-4 py-2 text-steel-500">{e.term_code}</td>
                  <td className="px-4 py-2 text-steel-700">
                    {e.course_code} · {e.course_title}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-steel-500">{e.credits}</td>
                  <td className="px-4 py-2 font-medium text-steel-800">{e.grade ?? "—"}</td>
                  <td className="px-4 py-2 text-steel-500">{e.status}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-steel-400">
                  No enrollments match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        <div className="flex items-center justify-between border-t border-steel-100 px-4 py-2.5">
          <span className="text-xs text-steel-400">
            Page {data?.page ?? 1} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex size-7 items-center justify-center rounded-md text-steel-500 hover:bg-steel-100 disabled:opacity-30"
            >
              <ChevronLeft className="size-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="flex size-7 items-center justify-center rounded-md text-steel-500 hover:bg-steel-100 disabled:opacity-30"
            >
              <ChevronRight className="size-4" />
            </button>
          </div>
        </div>
      </AdminCard>
    </div>
  );
}
