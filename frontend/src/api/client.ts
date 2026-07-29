import { ApiError } from '../types/apiError';

const TOKEN_KEY = 'invoice_reminder.access_token';
const USER_KEY = 'invoice_reminder.user';

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser<T>(): T | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function setStoredUser(user: unknown): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers ?? {}),
    },
  });

  if (!res.ok) {
    let body: { detail?: string; code?: string } = {};
    try {
      body = await res.json();
    } catch {
      /* non-JSON error body */
    }
    const err = new ApiError(res.status, body.code ?? 'unknown_error', body.detail ?? res.statusText);
    if (res.status === 401) {
      clearStoredToken();
    }
    throw err;
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const get = <T>(path: string): Promise<T> => request<T>(path);

export const post = <T>(path: string, body?: unknown): Promise<T> =>
  request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined });

export const patch = <T>(path: string, body: unknown): Promise<T> =>
  request<T>(path, { method: 'PATCH', body: JSON.stringify(body) });

export const del = <T>(path: string): Promise<T> => request<T>(path, { method: 'DELETE' });

export { ApiError };
