import { useEffect, useState } from "react";
import axios from "axios";

import { type AuthenticatedUser, loginWithTelegramMiniApp } from "./api/auth";
import { formatRupiah } from "./utils/currency";

type AuthState =
    | { status: "loading" }
    | { status: "authenticated"; user: AuthenticatedUser }
    | { status: "denied"; message: string };

function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") {
            return detail;
        }
    }
    if (error instanceof Error) {
        return error.message;
    }
    return "Akses tidak tersedia.";
}

export default function App() {
    const [authState, setAuthState] = useState<AuthState>({ status: "loading" });

    useEffect(() => {
        let isMounted = true;

        async function authenticate() {
            try {
                const auth = await loginWithTelegramMiniApp();
                localStorage.setItem("access_token", auth.access_token);
                if (isMounted) {
                    setAuthState({ status: "authenticated", user: auth.user });
                }
            } catch (error) {
                localStorage.removeItem("access_token");
                if (isMounted) {
                    setAuthState({ status: "denied", message: getErrorMessage(error) });
                }
            }
        }

        void authenticate();

        return () => {
            isMounted = false;
        };
    }, []);

    if (authState.status === "loading") {
        return (
            <main className="app-shell">
                <section className="hero-card" aria-busy="true">
                    <p className="eyebrow">Telegram Mini App</p>
                    <h1>Memuat...</h1>
                    <p className="description">Sedang memvalidasi akses Telegram kamu.</p>
                </section>
            </main>
        );
    }

    if (authState.status === "denied") {
        return (
            <main className="app-shell">
                <section className="hero-card access-denied" role="alert">
                    <p className="eyebrow">Akses ditolak</p>
                    <h1>Belum bisa masuk</h1>
                    <p className="description">{authState.message}</p>
                    <p className="note">
                        Pastikan akun Telegram kamu sudah terdaftar dan onboarding lewat bot
                        sudah selesai.
                    </p>
                </section>
            </main>
        );
    }

    return (
        <main className="app-shell">
            <section className="hero-card">
                <p className="eyebrow">Telegram Mini App</p>
                <h1>AI Expense Tracker</h1>
                <p className="description">
                    Halo {authState.user.first_name ?? "kamu"}, dashboard kamu siap
                    terhubung dengan autentikasi Telegram Mini App.
                </p>
                <dl className="summary-grid" aria-label="Contoh ringkasan bulanan">
                    <div>
                        <dt>Pemasukan</dt>
                        <dd>{formatRupiah(0)}</dd>
                    </div>
                    <div>
                        <dt>Pengeluaran</dt>
                        <dd>{formatRupiah(0)}</dd>
                    </div>
                    <div>
                        <dt>Cashflow</dt>
                        <dd>{formatRupiah(0)}</dd>
                    </div>
                </dl>
                <p className="note">
                    Autentikasi berhasil. Milestone berikutnya akan menghubungkan data
                    transaksi dan dashboard.
                </p>
            </section>
        </main>
    );
}
