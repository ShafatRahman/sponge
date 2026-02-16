import type { Session, SupabaseClient, Subscription } from "@supabase/supabase-js";
import { getSupabaseClient } from "@/lib/supabase/client";

export interface AuthResult {
  session: Session | null;
  error: string | null;
}

/**
 * Auth management service wrapping Supabase Auth.
 */
export class AuthService {
  private supabase: SupabaseClient;

  constructor(supabase?: SupabaseClient) {
    this.supabase = supabase ?? getSupabaseClient();
  }

  async signInWithEmail(email: string, password: string): Promise<AuthResult> {
    const { data, error } = await this.supabase.auth.signInWithPassword({
      email,
      password,
    });
    return {
      session: data.session,
      error: error?.message ?? null,
    };
  }

  async signUp(email: string, password: string): Promise<AuthResult> {
    const { data, error } = await this.supabase.auth.signUp({
      email,
      password,
    });
    return {
      session: data.session,
      error: error?.message ?? null,
    };
  }

  async signOut(): Promise<void> {
    await this.supabase.auth.signOut();
  }

  async getSession(): Promise<Session | null> {
    const {
      data: { session },
    } = await this.supabase.auth.getSession();
    return session;
  }

  onAuthStateChange(callback: (session: Session | null) => void): Subscription {
    const {
      data: { subscription },
    } = this.supabase.auth.onAuthStateChange((_event, session) => {
      callback(session);
    });
    return subscription;
  }
}
