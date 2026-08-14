import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAdminStudentDetail } from "../../lib/adminQueries";
import { AdminCard, StatusPill } from "../../components/admin/ui";

export default function AdminStudentDetail() {
  const { studentId } = useParams<{ studentId: string }>();
  const { data, isLoading } = useAdminStudentDetail(studentId);

  if (isLoading || !data) {
    return <p className="text-sm text-steel-400">Loading…</p>;
  }

  const { profile, terms, degree_progress } = data;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/admin/students"
          className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-steel-500 hover:text-steel-700"
        >
          <ArrowLeft className="size-3.5" /> Back to students
        </Link>
        <h1 className="text-xl font-semibold tracking-tight text-steel-900">
          {profile.first_name} {profile.last_name}
        </h1>
        <p className="mt-0.5 font-mono text-xs text-steel-500">{profile.student_id}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <AdminCard className="p-4 lg:col-span-1">
          <p className="mb-3 text-xs font-medium text-steel-400">Profile</p>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-xs text-steel-400">Programme</dt>
              <dd className="text-steel-800">{profile.program_name}</dd>
            </div>
            <div>
              <dt className="text-xs text-steel-400">Standing</dt>
              <dd><StatusPill status={profile.academic_status} /></dd>
            </div>
            <div>
              <dt className="text-xs text-steel-400">Advisor</dt>
              <dd className="text-steel-800">{profile.advisor_name}</dd>
            </div>
            <div>
              <dt className="text-xs text-steel-400">Entry / Expected grad</dt>
              <dd className="text-steel-800">
                {profile.entry_term} / {profile.expected_graduation_term}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-steel-400">Email</dt>
              <dd className="text-steel-800">{profile.email}</dd>
            </div>
            <div className="flex gap-6 pt-1">
              <div>
                <dt className="text-xs text-steel-400">GPA</dt>
                <dd className="text-lg font-semibold text-steel-900">{profile.cumulative_gpa ?? "N/A"}</dd>
              </div>
              <div>
                <dt className="text-xs text-steel-400">Credits</dt>
                <dd className="text-lg font-semibold text-steel-900">{profile.total_credits_earned}</dd>
              </div>
            </div>
          </dl>
        </AdminCard>

        <AdminCard className="p-4 lg:col-span-3">
          <p className="mb-3 text-xs font-medium text-steel-400">Degree progress</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {degree_progress.map((c) => (
              <div key={c.category_id} className="rounded-md border border-steel-100 p-3">
                <p className="mb-1 text-sm font-medium text-steel-800">{c.category_name}</p>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-steel-100">
                  <div
                    className="h-full bg-steel-600"
                    style={{
                      width: `${Math.min((c.credits_earned / c.credits_required) * 100, 100)}%`,
                    }}
                  />
                </div>
                <p className="mt-1.5 text-xs text-steel-500">
                  {c.credits_earned}/{c.credits_required} credits
                  {c.credits_in_progress > 0 && ` (+${c.credits_in_progress} in progress)`}
                </p>
              </div>
            ))}
          </div>
        </AdminCard>
      </div>

      <AdminCard className="overflow-hidden">
        <div className="border-b border-steel-100 px-4 py-3">
          <p className="text-xs font-medium text-steel-400">Enrollments by term</p>
        </div>
        <div className="divide-y divide-steel-50">
          {terms.map((t) => (
            <div key={t.term_code} className="px-4 py-3">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-sm font-medium text-steel-800">{t.term_name}</p>
                <span className="text-xs text-steel-500">Term GPA: {t.term_gpa ?? "N/A"}</span>
              </div>
              <table className="w-full text-left text-sm">
                <tbody className="divide-y divide-steel-50">
                  {t.courses.map((c) => (
                    <tr key={c.course_code}>
                      <td className="w-24 py-1 font-mono text-xs text-steel-500">{c.course_code}</td>
                      <td className="py-1 text-steel-700">{c.title}</td>
                      <td className="w-20 py-1 text-xs text-steel-500">{c.status}</td>
                      <td className="w-12 py-1 text-right font-medium text-steel-800">{c.grade ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </AdminCard>
    </div>
  );
}
