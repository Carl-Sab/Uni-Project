// The JWT lives only in memory (this module-level variable), never in
// localStorage/sessionStorage — sessionStorage only remembers the
// student_id so a page reload can silently re-authenticate (student login
// needs no password), not the token itself.
let token: string | null = null;

// Both AuthProvider (student) and AdminAuthProvider register a handler here
// - a plain single-slot handler would let whichever mounts second silently
// overwrite the other's, so a 401 on a student route could end up clearing
// admin state instead (or getting dropped entirely). Every registered
// handler runs on a 401; clearing already-null state in the inactive one
// is a harmless no-op.
const unauthorizedHandlers = new Set<() => void>();

export function getToken(): string | null {
  return token;
}

export function setToken(next: string | null): void {
  token = next;
}

export function onUnauthorized(handler: () => void): () => void {
  unauthorizedHandlers.add(handler);
  return () => unauthorizedHandlers.delete(handler);
}

export function triggerUnauthorized(): void {
  for (const handler of unauthorizedHandlers) handler();
}
