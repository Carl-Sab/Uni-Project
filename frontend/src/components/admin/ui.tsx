import type { ReactNode } from "react";

export function AdminCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-steel-200 bg-white ${className}`}>{children}</div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  indexed: "bg-good-100 text-good-500",
  approved: "bg-good-100 text-good-500",
  "Good standing": "bg-good-100 text-good-500",
  pending: "bg-amber-100 text-amber-500",
  indexing: "bg-steel-100 text-steel-600",
  failed: "bg-red-100 text-red-600",
  "Academic probation": "bg-amber-100 text-amber-500",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium ${
        STATUS_STYLES[status] ?? "bg-steel-100 text-steel-600"
      }`}
    >
      {status}
    </span>
  );
}

export function AdminButton({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  const styles = {
    primary: "bg-steel-700 text-white hover:bg-steel-800",
    secondary: "border border-steel-200 text-steel-700 hover:bg-steel-50",
    danger: "border border-red-200 text-red-600 hover:bg-red-50",
  }[variant];

  return (
    <button
      className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors duration-100 disabled:opacity-50 ${styles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
