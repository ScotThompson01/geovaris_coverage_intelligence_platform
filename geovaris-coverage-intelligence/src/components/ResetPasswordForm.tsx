"use client";

import Image from "next/image";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import {
    FormEvent,
    useState,
} from "react";

import { authClient } from "@/lib/auth-client";

const MIN_PASSWORD_LENGTH =
    8;

export default function ResetPasswordForm() {
    const searchParams =
        useSearchParams();

    const token =
        searchParams.get(
            "token",
        );

    const tokenError =
        searchParams.get(
            "error",
        );

    const [
        newPassword,
        setNewPassword,
    ] = useState("");

    const [
        confirmPassword,
        setConfirmPassword,
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

    const hasValidToken =
        Boolean(token) &&
        !tokenError;

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        setError("");
        setSuccess(false);

        if (!token) {
            setError(
                "This password reset link is invalid or has expired.",
            );

            return;
        }

        if (
            newPassword.length <
            MIN_PASSWORD_LENGTH
        ) {
            setError(
                `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`,
            );

            return;
        }

        if (
            newPassword !==
            confirmPassword
        ) {
            setError(
                "Passwords do not match.",
            );

            return;
        }

        setIsSubmitting(true);

        try {
            const result =
                await authClient.resetPassword({
                    newPassword,
                    token,
                });

            if (result.error) {
                setError(
                    result.error.message ??
                        "Unable to reset password.",
                );

                return;
            }

            setSuccess(true);
            setNewPassword("");
            setConfirmPassword("");
        } catch (err) {
            console.error(
                "Password reset failed:",
                err,
            );

            setError(
                "Unable to reset password.",
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
                        Choose a new password
                    </h1>

                    <p className="mt-2 text-sm leading-6 text-slate-500">
                        Set a new password for your GeoVaris account.
                    </p>
                </div>

                {tokenError ||
                !hasValidToken ? (
                    <div className="mt-7">
                        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                            This password reset link is invalid or has expired.
                        </p>

                        <div className="mt-5 text-center">
                            <Link
                                href="/forgot-password"
                                className="text-sm font-medium text-violet-600 hover:text-violet-700"
                            >
                                Request a new reset link
                            </Link>
                        </div>
                    </div>
                ) : success ? (
                    <div className="mt-7">
                        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                            Your password has been reset successfully.
                        </p>

                        <div className="mt-5 text-center">
                            <Link
                                href="/"
                                className="text-sm font-medium text-violet-600 hover:text-violet-700"
                            >
                                Return to sign in
                            </Link>
                        </div>
                    </div>
                ) : (
                    <form
                        className="mt-7 space-y-5"
                        onSubmit={
                            handleSubmit
                        }
                    >
                        <div>
                            <label
                                htmlFor="new-password"
                                className="text-sm font-medium text-slate-700"
                            >
                                New password
                            </label>

                            <input
                                id="new-password"
                                type="password"
                                autoComplete="new-password"
                                required
                                minLength={
                                    MIN_PASSWORD_LENGTH
                                }
                                value={
                                    newPassword
                                }
                                onChange={
                                    (event) =>
                                        setNewPassword(
                                            event.target.value,
                                        )
                                }
                                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
                            />
                        </div>

                        <div>
                            <label
                                htmlFor="confirm-password"
                                className="text-sm font-medium text-slate-700"
                            >
                                Confirm new password
                            </label>

                            <input
                                id="confirm-password"
                                type="password"
                                autoComplete="new-password"
                                required
                                minLength={
                                    MIN_PASSWORD_LENGTH
                                }
                                value={
                                    confirmPassword
                                }
                                onChange={
                                    (event) =>
                                        setConfirmPassword(
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
                                ? "Resetting password..."
                                : "Reset password"}
                        </button>
                    </form>
                )}
            </div>
        </main>
    );
}