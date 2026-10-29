export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : body.detail?.map((e: { msg: string }) => e.msg).join('; ') || message; } catch { /* non-JSON proxy error */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export const post = <T,>(path: string, value: unknown, signal?: AbortSignal) => api<T>(path, { method: 'POST', body: JSON.stringify(value), signal });
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please retry.';
