"use client";

import {
    useState,
} from "react";

import { authClient } from "@/lib/auth-client";

export default function SignOutButton() {
    const [
        isSigningOut,
        setIsSigningOut,
    ] = useState(false);

    async function handleSignOut() {
        setIsSigningOut(true);

        try {
            await authClient.signOut();

            window.location.href = "/";
        } catch (error) {
            console.error(
                "Sign-out failed:",
                error,
            );

            setIsSigningOut(false);
        }
    }

    return (
        <button
            type="button"
            onClick={
                handleSignOut
            }
            disabled={
                isSigningOut
            }
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
            {isSigningOut
                ? "Signing out..."
                : "Sign out"}
        </button>
    );
}