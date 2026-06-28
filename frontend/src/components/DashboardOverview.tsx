import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
    getCategoryBreakdown,
    getDashboardSummary,
    getMonthlyTrend,
    getRecentTransactions,
    type CategoryBreakdownItem,
    type DashboardSummary,
    type TrendItem,
} from "../api/dashboard";
import type { Transaction } from "../api/transactions";
import { formatRupiah } from "../utils/currency";

interface DashboardOverviewProps {
    token: string;
    firstName: string | null;
    isActive: boolean;
    refreshKey: number;
    onUnauthorized: (message: string) => void;
}

interface DashboardData {
    summary: DashboardSummary;
    categories: CategoryBreakdownItem[];
    trend: TrendItem[];
    recentTransactions: Transaction[];
}

function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") {
            return detail;
        }
    }
    return "Dashboard belum bisa dimuat. Coba lagi sebentar.";
}

function monthLabel(month: string): string {
    const [year, monthNumber] = month.split("-");
    return new Intl.DateTimeFormat("id-ID", {
        month: "short",
        year: "2-digit",
    }).format(new Date(Number(year), Number(monthNumber) - 1, 1));
}

function categoryLabel(category: string): string {
    return category.replace(/_/g, " ");
}

export function DashboardOverview({
    token,
    firstName,
    isActive,
    refreshKey,
    onUnauthorized,
}: DashboardOverviewProps) {
    const [data, setData] = useState<DashboardData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastLoadedRefreshKey, setLastLoadedRefreshKey] = useState<number | null>(null);

    const maxTrendAmount = useMemo(() => {
        if (!data?.trend.length) {
            return 0;
        }
        return Math.max(
            ...data.trend.map((item) => Math.max(item.income_total, item.expense_total)),
        );
    }, [data]);

    const loadDashboard = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const [summary, categories, trend, recentTransactions] = await Promise.all([
                getDashboardSummary(token),
                getCategoryBreakdown(token),
                getMonthlyTrend(token),
                getRecentTransactions(token),
            ]);
            setData({ summary, categories, trend, recentTransactions });
            setLastLoadedRefreshKey(refreshKey);
        } catch (requestError) {
            if (axios.isAxiosError(requestError) && requestError.response?.status === 401) {
                onUnauthorized("Sesi kamu sudah berakhir. Silakan buka ulang Mini App.");
                return;
            }
            setError(errorMessage(requestError));
        } finally {
            setIsLoading(false);
        }
    }, [onUnauthorized, refreshKey, token]);

    useEffect(() => {
        if (!isActive) {
            return;
        }
        if (lastLoadedRefreshKey === refreshKey) {
            return;
        }
        void loadDashboard();
    }, [isActive, lastLoadedRefreshKey, loadDashboard, refreshKey]);

    if (isLoading) {
        return (
            <section className="hero-card dashboard-overview" aria-busy="true">
                <p className="eyebrow">Dashboard</p>
                <h1>Memuat ringkasan...</h1>
                <p className="description">Sedang menghitung ringkasan keuangan kamu.</p>
            </section>
        );
    }

    if (error || !data) {
        return (
            <section className="hero-card dashboard-overview" role="alert">
                <p className="eyebrow">Dashboard</p>
                <h1>Belum bisa memuat data</h1>
                <p className="description">{error ?? "Data dashboard tidak tersedia."}</p>
                <button className="secondary-button" type="button" onClick={() => void loadDashboard()}>
                    Coba lagi
                </button>
            </section>
        );
    }

    const hasAnyData =
        data.summary.income_total > 0 ||
        data.summary.expense_total > 0 ||
        data.recentTransactions.length > 0;

    return (
        <section className="hero-card dashboard-overview" aria-labelledby="dashboard-title">
            <p className="eyebrow">Dashboard</p>
            <h1 id="dashboard-title">Halo {firstName ?? "kamu"}</h1>
            <p className="description">
                Ringkasan bulan {data.summary.month} berdasarkan transaksi yang kamu catat.
            </p>

            <dl className="summary-grid" aria-label="Ringkasan bulanan">
                <div>
                    <dt>Pemasukan</dt>
                    <dd>{formatRupiah(data.summary.income_total)}</dd>
                </div>
                <div>
                    <dt>Pengeluaran</dt>
                    <dd>{formatRupiah(data.summary.expense_total)}</dd>
                </div>
                <div>
                    <dt>Cashflow</dt>
                    <dd>{formatRupiah(data.summary.net_cashflow)}</dd>
                </div>
                <div>
                    <dt>Savings rate</dt>
                    <dd>{data.summary.savings_rate_percent}%</dd>
                </div>
            </dl>

            {!hasAnyData ? (
                <div className="list-state" role="status">
                    Belum ada data bulan ini. Tambahkan transaksi untuk melihat ringkasan.
                </div>
            ) : null}

            <div className="dashboard-grid">
                <section className="dashboard-card" aria-labelledby="category-title">
                    <h2 id="category-title">Kategori pengeluaran</h2>
                    {data.categories.length === 0 ? (
                        <p className="muted-text">Belum ada pengeluaran bulan ini.</p>
                    ) : (
                        <ul className="breakdown-list">
                            {data.categories.map((item) => (
                                <li key={item.category}>
                                    <div className="breakdown-row">
                                        <span>{categoryLabel(item.category)}</span>
                                        <strong>{formatRupiah(item.amount)}</strong>
                                    </div>
                                    <div className="progress-track" aria-hidden="true">
                                        <span style={{ width: `${item.percent}%` }} />
                                    </div>
                                    <small>{item.percent}% dari pengeluaran</small>
                                </li>
                            ))}
                        </ul>
                    )}
                </section>

                <section className="dashboard-card" aria-labelledby="trend-title">
                    <h2 id="trend-title">Tren bulanan</h2>
                    <ul className="trend-list" aria-label="Tren pemasukan dan pengeluaran">
                        {data.trend.map((item) => (
                            <li key={item.month}>
                                <span>{monthLabel(item.month)}</span>
                                <div className="trend-bars">
                                    <span
                                        className="income-bar"
                                        style={{
                                            width: maxTrendAmount
                                                ? `${(item.income_total / maxTrendAmount) * 100}%`
                                                : "0%",
                                        }}
                                    />
                                    <span
                                        className="expense-bar"
                                        style={{
                                            width: maxTrendAmount
                                                ? `${(item.expense_total / maxTrendAmount) * 100}%`
                                                : "0%",
                                        }}
                                    />
                                </div>
                                <strong>{formatRupiah(item.net_cashflow)}</strong>
                            </li>
                        ))}
                    </ul>
                </section>
            </div>

            <section className="dashboard-card recent-card" aria-labelledby="recent-title">
                <h2 id="recent-title">Transaksi terbaru</h2>
                {data.recentTransactions.length === 0 ? (
                    <p className="muted-text">Belum ada transaksi terbaru.</p>
                ) : (
                    <ul className="recent-list">
                        {data.recentTransactions.map((transaction) => (
                            <li key={transaction.id}>
                                <span>{transaction.name}</span>
                                <strong>
                                    {transaction.type === "income" ? "+" : "-"}
                                    {formatRupiah(transaction.amount)}
                                </strong>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
        </section>
    );
}
