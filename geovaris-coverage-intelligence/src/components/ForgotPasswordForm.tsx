"use client";

import Image from "next/image";
import Link from "next/link";

import {
    FormEvent,
    useState,
} from "react";

import { authClient } from "@/lib/auth-client";

export default function ForgotPasswordForm() {
    const [
        email,
        setEmail,
    ] = useState("");

    const [
        error,
        setError,
    ] = useState("");

    const [
        success,
        setSuccess,
    ] = useState(false);

    const [
        isSubmitting,
        setIsSubmitting,
    ] = useState(false);

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        setError("");
        setSuccess(false);
        setIsSubmitting(true);

        try {
            const redirectTo =
                `${window.location.origin}/reset-password`;

            const result =
                await authClient.requestPasswordReset({
                    email,
                    redirectTo,
                });

            if (result.error) {
                setError(
                    result.error.message ??
                        "Unable to request a password reset.",
                );

                return;
            }

            /*
             * Keep this message generic so the UI does not
             * disclose whether an account exists.
             */
            setSuccess(true);
        } catch (err) {
            console.error(
                "Password reset request failed:",
                err,
            );

            setError(
                "Unable to request a password reset.",
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
            <div className="w-full max-w-md rounded-2xl border-2 border-violet-500 bg-white p-8 shadow-[0_18px_55px_rgba(79,70,229,0.12)]">
                <div className="text-center">
                    <Image
                        src="/branding/geovaris-logo-color.svg"
                        alt="GeoVaris"
                        width={420}
                        height={136}
                        priority
                        className="mx-auto h-auto w-full max-w-[320px]"
                    />

                    <p className="mt-6 text-xs font-semibold uppercase tracking-wider text-violet-600">
                        Secure Access
                    </p>

                    <h1 className="mt-2 text-2xl font-semibold text-slate-900">
                        Reset your password
                    </h1>

                    <p className="mt-2 text-sm leading-6 text-slate-500">
                        Enter your account email to request a password reset.
                    </p>
                </div>

                <form
                    className="mt-7 space-y-5"
                    onSubmit={
                        handleSubmit
                    }
                >
                    <div>
                        <label
                            htmlFor="email"
                            className="text-sm font-medium text-slate-700"
                        >
                            Email
                        </label>

                        <input
                            id="email"
                            type="email"
                            autoComplete="email"
                            required
                            value={email}
                            onChange={
                                (event) =>
                                    setEmail(
                                        event.target.value,
                                    )
                            }
                            className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                        />
                    </div>

                    {success ? (
                        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                            If an account exists for that email address, password
                            reset instructions have been generated.
                        </p>
                    ) : null}

                    {error ? (
                        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                            {error}
                        </p>
                    ) : null}

                    <button
                        type="submit"
                        disabled={
                            isSubmitting
                        }
                        className="w-full rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:from-violet-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isSubmitting
                            ? "Requesting reset..."
                            : "Request password reset"}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <Link
                        href="/"
                        className="text-sm font-medium text-violet-600 hover:text-violet-700"
                    >
                        Back to sign in
                    </Link>
                </div>

                <p className="mt-6 border-t border-slate-100 pt-5 text-center text-xs text-slate-400">
                    Local/demo reset links are written to the GeoVaris server
                    console.
                </p>
            </div>
        </main>
    );
}