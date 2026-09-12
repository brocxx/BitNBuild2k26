import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  supabase,
  signInWithPassword,
  signOut as supabaseSignOut,
  getDevEmail,
} from "./supabase";
import { API_MODE } from "../api";

type AuthState = {
  loading: boolean;
  session: Session | null;
  devUser: string | null;
  isAuthenticated: boolean;
  signIn: (email: string, password?: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [devUser, setDevUser] = useState<string | null>(() => getDevEmail());
  const [loading, setLoading] = useState(API_MODE === "real" && !!supabase);

  useEffect(() => {
    if (API_MODE !== "real" || !supabase) {
      setLoading(false);
      return;
    }
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => sub.subscription.unsubscribe();
  }, []);

  const isAuthenticated = API_MODE === "mock" ? true : !!(session || devUser);

  const value = useMemo<AuthState>(
    () => ({
      loading,
      session,
      devUser,
      isAuthenticated,
      signIn: async (email: string, password?: string) => {
        const res = await signInWithPassword(email, password);
        if (typeof res === "string") {
          setDevUser(email);
        } else {
          setSession(res);
        }
      },
      signOut: async () => {
        await supabaseSignOut();
        setSession(null);
        setDevUser(null);
      },
    }),
    [loading, session, devUser, isAuthenticated]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
