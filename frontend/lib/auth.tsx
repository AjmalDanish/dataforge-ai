"use client";

/**
 * Auth wrapper around Clerk.
 *
 * Clerk is enabled when NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is set (production).
 * Without it (local dev, CI) the app runs in "dev mode": everyone counts as
 * signed in and no token is sent, matching the API's dev mode (no CLERK_ISSUER).
 * CLERK_ENABLED is a build-time constant, so the conditional hook calls below
 * are stable across renders. ClerkProvider itself is rendered in app/layout.tsx
 * (it must be a server component).
 */

import {
  SignInButton,
  SignedIn,
  SignedOut,
  UserButton,
  useAuth,
} from "@clerk/nextjs";
import { useCallback } from "react";

export const CLERK_ENABLED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

/** Returns a function that resolves to a fresh session token (or null when signed out / dev mode). */
export function useApiToken(): () => Promise<string | null> {
  if (!CLERK_ENABLED) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useCallback(async () => null, []);
  }
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const { getToken } = useAuth();
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useCallback(() => getToken(), [getToken]);
}

/** `undefined` while Clerk loads, then true/false. Always true in dev mode. */
export function useSignedIn(): boolean | undefined {
  if (!CLERK_ENABLED) return true;
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const { isLoaded, isSignedIn } = useAuth();
  return isLoaded ? Boolean(isSignedIn) : undefined;
}

export function AuthButtons() {
  if (!CLERK_ENABLED) return null;
  return (
    <>
      <SignedOut>
        <SignInButton mode="modal">
          <button className="rounded border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-900">Sign in</button>
        </SignInButton>
      </SignedOut>
      <SignedIn>
        <UserButton />
      </SignedIn>
    </>
  );
}

export function SignInPrompt({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-center">
      <p className="text-sm text-slate-300">{message}</p>
      {CLERK_ENABLED && (
        <SignInButton mode="modal">
          <button className="mt-4 rounded bg-emerald-500 px-5 py-2 font-semibold text-slate-950 hover:bg-emerald-400">Sign in</button>
        </SignInButton>
      )}
    </div>
  );
}
