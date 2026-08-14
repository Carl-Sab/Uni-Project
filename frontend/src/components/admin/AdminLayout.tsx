import { Outlet } from "react-router-dom";
import { AdminSidebar } from "./AdminSidebar";

export function AdminLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-steel-50">
      <AdminSidebar />
      <main className="min-w-0 flex-1 overflow-y-auto">
        {/* Deliberately no page-transition animation here (unlike the
            student portal) - admin work is scanning and repeat clicking,
            and a fade/rise on every navigation would slow that down for
            no benefit. */}
        <div className="mx-auto max-w-6xl px-8 py-7">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
