import {
    Suspense,
} from "react";

import ResetPasswordForm from "@/components/ResetPasswordForm";

function ResetPasswordFallback() {
    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
            <div className="w-full max-w-md rounded-2xl border-2 border-violet-500 bg-white p-8 text-center shadow-[0_18px_55px_rgba(79,70,229,0.12)]">
                <p className="text-sm text-slate-500">
                    Loading password reset...
                </p>
            </div>
        </main>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense
            fallback={
                <ResetPasswordFallback />
            }
        >
            <ResetPasswordForm />
        </Suspense>
    );
}