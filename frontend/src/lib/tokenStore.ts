// The JWT lives only in memory (this module-level variable), never in
// localStorage/sessionStorage — sessionStorage only remembers the
// student_id so a page reload can silently re-authenticate (student login
// needs no password), not the token itself.
let token: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function getToken(): string | null {
  return token;
}

export function setToken(next: string | null): void {
  token = next;
}

export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler;
}

export function triggerUnauthorized(): void {
  unauthorizedHandler?.();
}
