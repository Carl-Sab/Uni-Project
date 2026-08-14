import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-ink-900">{children}</strong>,
        ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-1 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal space-y-1 last:mb-0">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        h1: ({ children }) => <h3 className="mb-1.5 mt-3 text-base font-semibold text-ink-900 first:mt-0">{children}</h3>,
        h2: ({ children }) => <h3 className="mb-1.5 mt-3 text-base font-semibold text-ink-900 first:mt-0">{children}</h3>,
        h3: ({ children }) => <h4 className="mb-1 mt-2 text-sm font-semibold text-ink-900 first:mt-0">{children}</h4>,
        hr: () => <hr className="my-3 border-ink-100" />,
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noreferrer" className="text-brand-600 underline decoration-brand-300 underline-offset-2 hover:text-brand-700">
            {children}
          </a>
        ),
        table: ({ children }) => (
          <div className="mb-2 overflow-x-auto rounded-lg border border-ink-100">
            <table className="w-full border-collapse text-xs">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-ink-50">{children}</thead>,
        th: ({ children }) => (
          <th className="border-b border-ink-100 px-2.5 py-1.5 text-left font-medium text-ink-700">{children}</th>
        ),
        td: ({ children }) => <td className="border-b border-ink-50 px-2.5 py-1.5 text-ink-700">{children}</td>,
        code: ({ children }) => (
          <code className="rounded bg-ink-100 px-1 py-0.5 text-[0.85em] text-ink-900">{children}</code>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
