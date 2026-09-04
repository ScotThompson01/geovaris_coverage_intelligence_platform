"use client";

import Image from "next/image";
import Link from "next/link";

import {
    FormEvent,
    useState,
} from "react";

import { authClient } from "@/lib/auth-client";

export default function SignInForm() {
    const [
        email,
        setEmail,
    ] = useState("");

    const [
        password,
        setPassword,
    ] = useState("");

    const [
        error,
        setError,
    ] = useState("");

    const [
        isSubmitting,
        setIsSubmitting,
    ] = useState(false);

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        setError("");
        setIsSubmitting(true);

        try {
            const result =
                await authClient.signIn.email({
                    email,
                    password,
                });

            if (result.error) {
                setError(
                    result.error.message ??
                        "Unable to sign in.",
                );

                return;
            }

            window.location.href = "/";
        } catch (err) {
            console.error(
                "Sign-in failed:",
                err,
            );

            setError(
                "Unable to sign in.",
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-50 px-6 py-12">
            <div
                aria-hidden="true"
                className="pointer-events-none absolute -left-56 top-1/2 h-[620px] w-[620px] -translate-y-1/2 rounded-full border border-indigo-100"
            />

            <div
                aria-hidden="true"
                className="pointer-events-none absolute -left-44 top-1/2 h-[520px] w-[520px] -translate-y-1/2 rounded-full border border-indigo-100"
            />

            <div
                aria-hidden="true"
                className="pointer-events-none absolute -right-56 top-1/2 h-[620px] w-[620px] -translate-y-1/2 rounded-full border border-indigo-100"
            />

            <div
                aria-hidden="true"
                className="pointer-events-none absolute -right-44 top-1/2 h-[520px] w-[520px] -translate-y-1/2 rounded-full border border-indigo-100"
            />

            <div className="relative z-10 w-full max-w-3xl">
                <div className="mb-7 text-center">
                    <div className="flex w-full justify-center">
                        <Image
                            src="/branding/geovaris-logo-color.svg"
                            alt="GeoVaris"
                            width={840}
                            height={272}
                            priority
                            className="h-auto w-full max-w-[720px] md:relative md:left-20"
                        />
                    </div>

                    <h1 className="mt-6 text-3xl font-semibold tracking-tight text-slate-900">
                        GeoVaris Coverage Intelligence
                    </h1>

                    <p className="mt-2 text-sm text-slate-500">
                        Clean data. Confident results.
                    </p>
                </div>

                <div className="overflow-hidden rounded-2xl border-2 border-violet-500 bg-white shadow-[0_18px_55px_rgba(79,70,229,0.12)]">
                    <div className="grid md:grid-cols-[0.95fr_1.05fr]">
                        <div className="flex items-center justify-center border-b border-slate-200 bg-gradient-to-br from-violet-50 via-white to-cyan-50 p-8 md:border-b-0 md:border-r">
                            <div className="text-center">
                                <Image
                                    src="/branding/coverage-intelligence-platform.png"
                                    alt="GeoVaris Coverage Intelligence Platform"
                                    width={360}
                                    height={360}
                                    priority
                                    className="mx-auto h-auto w-full max-w-[260px]"
                                />

                                <p className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
                                    Coverage Intelligence Platform
                                </p>
                            </div>
                        </div>

                        <div className="p-8 md:p-10">
                            <p className="text-xs font-semibold uppercase tracking-wider text-violet-600">
                                Secure Access
                            </p>

                            <h2 className="mt-2 text-2xl font-semibold text-slate-900">
                                Sign in
                            </h2>

                            <p className="mt-2 text-sm leading-6 text-slate-500">
                                Sign in to access your GeoVaris customer workspace.
                            </p>

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

                                <div>
                                    <div className="flex items-center justify-between gap-4">
                                        <label
                                            htmlFor="password"
                                            className="text-sm font-medium text-slate-700"
                                        >
                                            Password
                                        </label>

                                        <Link
                                            href="/forgot-password"
                                            className="text-sm font-medium text-violet-600 hover:text-violet-700"
                                        >
                                            Forgot password?
                                        </Link>
                                    </div>

                                    <input
                                        id="password"
                                        type="password"
                                        autoComplete="current-password"
                                        required
                                        value={password}
                                        onChange={
                                            (event) =>
                                                setPassword(
                                                    event.target.value,
                                                )
                                        }
                                        className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                                    />
                                </div>

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
                                        ? "Signing in..."
                                        : "Sign in"}
                                </button>
                            </form>

                            <div className="mt-7 border-t border-slate-100 pt-5">
                                <p className="text-center text-xs text-slate-400">
                                    Secure GeoVaris customer access
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}