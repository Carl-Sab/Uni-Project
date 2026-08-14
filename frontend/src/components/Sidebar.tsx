import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  CalendarDays,
  History,
  Target,
  BookOpen,
  CalendarCheck,
  LogOut,
  GraduationCap,
} from "lucide-react";
import { useAuth } from "../lib/AuthContext";
import { useProfile } from "../lib/queries";

const NAV = [
  { to: "/portal", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/portal/schedule", label: "Schedule", icon: CalendarDays },
  { to: "/portal/history", label: "History", icon: History },
  { to: "/portal/progress", label: "Degree Progress", icon: Target },
  { to: "/portal/courses", label: "Catalogue", icon: BookOpen },
  { to: "/portal/appointments", label: "Appointments", icon: CalendarCheck },
];

export function Sidebar() {
  const { logout } = useAuth();
  const { data: profile } = useProfile();

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-ink-100 bg-white">
      <div className="flex items-center gap-2 px-6 py-6">
        <div className="flex size-8 items-center justify-center rounded-lg bg-brand-600 text-white">
          <GraduationCap className="size-4.5" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-ink-900">Eurisko</span>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? "bg-brand-600 text-white shadow-sm shadow-brand-600/20"
                  : "text-ink-500 hover:bg-brand-50 hover:text-brand-700"
              }`
            }
          >
            <Icon className="size-4.5 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-ink-100 p-4">
        {profile ? (
          <div className="mb-3 px-2">
            <p className="truncate text-sm font-medium text-ink-900">
              {profile.first_name} {profile.last_name}
            </p>
            <p className="truncate text-xs text-ink-500">{profile.student_id}</p>
          </div>
        ) : null}
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-ink-500 transition-colors duration-150 hover:bg-ink-50 hover:text-ink-900"
        >
          <LogOut className="size-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
