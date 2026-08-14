import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  Users,
  BookOpen,
  ListChecks,
  SlidersHorizontal,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { useAdminAuth } from "../../lib/AdminAuthContext";

const NAV = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/documents", label: "Documents", icon: FileText },
  { to: "/admin/students", label: "Students", icon: Users },
  { to: "/admin/courses", label: "Courses", icon: BookOpen },
  { to: "/admin/enrollments", label: "Enrollments", icon: ListChecks },
  { to: "/admin/config", label: "Assistant Config", icon: SlidersHorizontal },
];

export function AdminSidebar() {
  const { username, logout } = useAdminAuth();

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-steel-800 bg-steel-950">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex size-7 items-center justify-center rounded-md bg-steel-700 text-steel-100">
          <ShieldCheck className="size-4" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight text-steel-50">Eurisko Admin</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-2.5">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] font-medium transition-colors duration-100 ${
                isActive
                  ? "bg-steel-800 text-steel-50"
                  : "text-steel-400 hover:bg-steel-900 hover:text-steel-100"
              }`
            }
          >
            <Icon className="size-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-steel-800 p-3">
        <div className="mb-2 px-2">
          <p className="truncate text-xs font-medium text-steel-200">{username}</p>
          <p className="text-[11px] text-steel-500">Administrator</p>
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-[13px] font-medium text-steel-400 transition-colors duration-100 hover:bg-steel-900 hover:text-steel-100"
        >
          <LogOut className="size-3.5" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
