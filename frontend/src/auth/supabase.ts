import { createClient, type Session } from "@supabase/supabase-js";

// Publishable key only — safe for the browser.
const url = import.meta.env.VITE_SUPABASE_URL;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

export const supabase = url && key ? createClient(url, key) : null;

const DEV_TOKEN_KEY = "kib_dev_token";

export async function getAccessToken(): Promise<string | null> {
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) {
      return data.session.access_token;
    }
  }
  return localStorage.getItem(DEV_TOKEN_KEY);
}

export function setDevToken(email: string): string {
  const cleanEmail = email.startsWith("dev:") ? email.slice(4) : email;
  const token = `dev:${cleanEmail.trim().toLowerCase()}`;
  localStorage.setItem(DEV_TOKEN_KEY, token);
  return token;
}

export function getDevEmail(): string | null {
  const token = localStorage.getItem(DEV_TOKEN_KEY);
  if (!token) return null;
  return token.startsWith("dev:") ? token.slice(4) : token;
}

export function clearDevToken(): void {
  localStorage.removeItem(DEV_TOKEN_KEY);
}

export async function signInWithPassword(email: string, password?: string): Promise<Session | string> {
  if (supabase) {
    if (!password) {
      throw new Error("Password is required for Supabase login.");
    }
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    if (!data.session) throw new Error("No session returned from Supabase.");
    return data.session;
  }
  // Local dev mode token
  return setDevToken(email);
}

export async function signOut(): Promise<void> {
  clearDevToken();
  if (supabase) {
    await supabase.auth.signOut();
  }
}
