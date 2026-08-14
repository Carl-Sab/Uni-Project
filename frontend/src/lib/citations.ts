export interface Citation {
  raw: string;
}

// Matches parenthetical citations like "(Student Handbook, p.2, §2.3)" or
// "(Student Handbook, p.2, §2.3; p.4, §5)" and splits multi-part ones on ';'.
const CITATION_RE = /\(([^()]*\bp\.\s?\d+[^()]*)\)/g;

export function extractCitations(text: string): Citation[] {
  const seen = new Set<string>();
  const out: Citation[] = [];
  for (const match of text.matchAll(CITATION_RE)) {
    for (const part of match[1].split(";")) {
      const raw = part.trim();
      if (raw && !seen.has(raw)) {
        seen.add(raw);
        out.push({ raw });
      }
    }
  }
  return out;
}
