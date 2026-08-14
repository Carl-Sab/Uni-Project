import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Sidebar } from "./Sidebar";
import { ChatPanel } from "./chat/ChatPanel";

export function Layout() {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-ink-50">
      <Sidebar />
      <main className="min-w-0 flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto max-w-5xl px-8 py-8"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
      <ChatPanel />
    </div>
  );
}
