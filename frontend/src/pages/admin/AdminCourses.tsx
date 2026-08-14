import { useState } from "react";
import { Search } from "lucide-react";
import { useAdminCourses } from "../../lib/adminQueries";
import { AdminCard } from "../../components/admin/ui";

export default function AdminCourses() {
  const { data: courses, isLoading } = useAdminCourses();
  const [query, setQuery] = useState("");

  const filtered = (courses ?? []).filter(
    (c) =>
      c.course_code.toLowerCase().includes(query.toLowerCase()) ||
      c.title.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-steel-900">Courses</h1>
          <p className="mt-0.5 text-sm text-steel-500">{courses?.length ?? 0} courses in the catalogue.</p>
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-steel-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search…"
            className="w-52 rounded-md border border-steel-200 py-1.5 pl-8 pr-3 text-sm text-steel-800 placeholder:text-steel-400 focus:border-steel-400 focus:outline-none"
          />
        </div>
      </div>

      <AdminCard className="overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-steel-100 bg-steel-50 text-xs font-medium text-steel-500">
            <tr>
              <th className="px-4 py-2.5">Code</th>
              <th className="px-4 py-2.5">Title</th>
              <th className="px-4 py-2.5">Credits</th>
              <th className="px-4 py-2.5">Prerequisites</th>
              <th className="px-4 py-2.5">Categories</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-steel-50">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-steel-400">
                  Loading…
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr key={c.course_code} className="hover:bg-steel-50/60">
                  <td className="px-4 py-2 font-mono text-xs text-steel-600">{c.course_code}</td>
                  <td className="px-4 py-2 font-medium text-steel-800">{c.title}</td>
                  <td className="px-4 py-2 tabular-nums text-steel-500">{c.credits}</td>
                  <td className="px-4 py-2 text-steel-500">
                    {c.prerequisites.length > 0 ? c.prerequisites.join(", ") : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex flex-wrap gap-1">
                      {c.categories.map((cat) => (
                        <span
                          key={cat}
                          className="rounded bg-steel-100 px-1.5 py-0.5 text-[11px] text-steel-600"
                        >
                          {cat}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </AdminCard>
    </div>
  );
}
