import { useEffect, useState } from "react";
import axios from "axios";

import { type AuthenticatedUser, loginWithTelegramMiniApp } from "./api/auth";
import logoUrl from "./assets/logo.svg";
import { DashboardOverview } from "./components/DashboardOverview";
import { BudgetPanel } from "./components/BudgetPanel";
import { InsightPanel } from "./components/InsightPanel";
import { PageHeader } from "./components/PageHeader";
import { PageMenu, type PageMenuTarget } from "./components/PageMenu";
import { SettingsPanel } from "./components/SettingsPanel";
import { TransactionsPanel } from "./components/TransactionsPanel";

type AuthState =
    | { status: "loading" }
    | { status: "authenticated"; token: string; user: AuthenticatedUser }
    | { status: "denied"; message: string };

type ActivePage = "dashboard" | PageMenuTarget;

function BrandHeader({ compact = false }: { compact?: boolean }) {
    return (
        <div className={compact ? "brand-header compact" : "brand-header"}>
            <img src={logoUrl} alt="The Tirtayasa" className="brand-logo" />
            <div>
                <p className="brand-name">The Tirtayasa</p>
                <p className="brand-tagline">Your AI Expense Tracker</p>
            </div>
        </div>
    );
}

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
    const [activePage, setActivePage] = useState<ActivePage>("dashboard");
    const [visitedPages, setVisitedPages] = useState<Set<ActivePage>>(
        () => new Set(["dashboard"]),
    );
    const [dashboardRefreshKey, setDashboardRefreshKey] = useState(0);
    const [budgetRefreshKey, setBudgetRefreshKey] = useState(0);
    const [advisorRefreshKey, setAdvisorRefreshKey] = useState(0);
    const [settingsRefreshKey, setSettingsRefreshKey] = useState(0);

    useEffect(() => {
        let isMounted = true;

        async function authenticate() {
            try {
                const auth = await loginWithTelegramMiniApp();
                localStorage.setItem("access_token", auth.access_token);
                if (isMounted) {
                    setActivePage("dashboard");
                    setVisitedPages(new Set(["dashboard"]));
                    setAuthState({
                        status: "authenticated",
                        token: auth.access_token,
                        user: auth.user,
                    });
                }
            } catch (error) {
                localStorage.removeItem("access_token");
                if (isMounted) {
                    setActivePage("dashboard");
                    setVisitedPages(new Set(["dashboard"]));
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
                    <BrandHeader />
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
                    <BrandHeader />
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

    const openPage = (page: ActivePage) => {
        setVisitedPages((current) => new Set(current).add(page));
        setActivePage(page);
        const prefersReducedMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)",
        ).matches;
        window.scrollTo({
            top: 0,
            behavior: prefersReducedMotion ? "auto" : "smooth",
        });
    };

    const handleUnauthorized = (message: string) => {
        localStorage.removeItem("access_token");
        setActivePage("dashboard");
        setVisitedPages(new Set(["dashboard"]));
        setAuthState({ status: "denied", message });
    };

    const markTransactionDataChanged = () => {
        setDashboardRefreshKey((value) => value + 1);
        setBudgetRefreshKey((value) => value + 1);
        setAdvisorRefreshKey((value) => value + 1);
    };

    const markBudgetDataChanged = () => {
        setAdvisorRefreshKey((value) => value + 1);
    };

    const handleCashflowPeriodChanged = (startDay: number) => {
        setAuthState((current) => {
            if (current.status !== "authenticated") {
                return current;
            }
            return {
                ...current,
                user: {
                    ...current.user,
                    cashflow_period_start_day: startDay,
                },
            };
        });
        setDashboardRefreshKey((value) => value + 1);
        setBudgetRefreshKey((value) => value + 1);
        setAdvisorRefreshKey((value) => value + 1);
        setSettingsRefreshKey((value) => value + 1);
    };

    return (
        <main className="app-shell dashboard-shell">
            <header className="dashboard-brand" aria-label="The Tirtayasa">
                <BrandHeader compact />
            </header>

            {visitedPages.has("dashboard") ? (
                <div className="page-panel" hidden={activePage !== "dashboard"}>
                    <DashboardOverview
                        token={authState.token}
                        firstName={authState.user.first_name}
                        isActive={activePage === "dashboard"}
                        refreshKey={dashboardRefreshKey}
                        onUnauthorized={handleUnauthorized}
                    />
                    <PageMenu onOpen={openPage} />
                </div>
            ) : null}

            {visitedPages.has("budget") ? (
                <div className="page-panel" hidden={activePage !== "budget"}>
                    <PageHeader
                        titleId="budget-page-title"
                        title="Budget"
                        description="Atur batas pengeluaran per kategori dan lihat progres bulan ini."
                        onBack={() => openPage("dashboard")}
                    />
                    <BudgetPanel
                        token={authState.token}
                        isActive={activePage === "budget"}
                        refreshKey={budgetRefreshKey}
                        onDataChanged={markBudgetDataChanged}
                        onUnauthorized={handleUnauthorized}
                    />
                </div>
            ) : null}

            {visitedPages.has("advisor") ? (
                <div className="page-panel" hidden={activePage !== "advisor"}>
                    <PageHeader
                        titleId="advisor-page-title"
                        title="AI Advisor"
                        description="Tanyakan kondisi cashflow, kebiasaan belanja, dan peluang penghematan berdasarkan data kamu."
                        onBack={() => openPage("dashboard")}
                    />
                    <InsightPanel
                        token={authState.token}
                        isActive={activePage === "advisor"}
                        refreshKey={advisorRefreshKey}
                        onUnauthorized={handleUnauthorized}
                    />
                </div>
            ) : null}

            {visitedPages.has("transactions") ? (
                <div className="page-panel" hidden={activePage !== "transactions"}>
                    <PageHeader
                        titleId="transactions-page-title"
                        title="Transaksi"
                        description="Kelola pemasukan dan pengeluaran manual."
                        onBack={() => openPage("dashboard")}
                    />
                    <TransactionsPanel
                        token={authState.token}
                        isActive={activePage === "transactions"}
                        refreshKey={0}
                        onDataChanged={markTransactionDataChanged}
                        onUnauthorized={handleUnauthorized}
                    />
                </div>
            ) : null}

            {visitedPages.has("settings") ? (
                <div className="page-panel" hidden={activePage !== "settings"}>
                    <PageHeader
                        titleId="settings-page-title"
                        title="Pengaturan"
                        description="Atur periode cashflow agar Dashboard dan Budget mengikuti siklus gajian kamu."
                        onBack={() => openPage("dashboard")}
                    />
                    <SettingsPanel
                        token={authState.token}
                        isActive={activePage === "settings"}
                        refreshKey={settingsRefreshKey}
                        onCashflowPeriodChanged={handleCashflowPeriodChanged}
                        onUnauthorized={handleUnauthorized}
                    />
                </div>
            ) : null}
        </main>
    );
}
