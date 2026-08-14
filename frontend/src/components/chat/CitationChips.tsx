import { FileText } from "lucide-react";
import { extractCitations } from "../../lib/citations";

export function CitationChips({ text }: { text: string }) {
  const citations = extractCitations(text);
  if (citations.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {citations.map((c, i) => (
        <span
          key={c.raw + i}
          className="inline-flex items-center gap-1 rounded-full border border-ink-100 bg-ink-50 px-2 py-0.5 text-[11px] font-medium text-ink-500"
          title={c.raw}
        >
          <FileText className="size-3" />
          {i + 1}. {c.raw}
        </span>
      ))}
    </div>
  );
}
