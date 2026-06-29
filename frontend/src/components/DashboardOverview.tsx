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
    if (/^\d{4}-\d{2}-\d{2}$/.test(month)) {
        const [year, monthNumber, day] = month.split("-").map(Number);
        return new Intl.DateTimeFormat("id-ID", {
            day: "numeric",
            month: "short",
            year: "2-digit",
        }).format(new Date(year, monthNumber - 1, day));
    }
    const [year, monthNumber] = month.split("-");
    return new Intl.DateTimeFormat("id-ID", {
        month: "short",
        year: "2-digit",
    }).format(new Date(Number(year), Number(monthNumber) - 1, 1));
}

function categoryLabel(category: string): string {
    return category.replace(/_/g, " ");
}

function periodLabel(period: string): string {
    if (/^\d{4}-\d{2}-\d{2}$/.test(period)) {
        const [year, month, day] = period.split("-").map(Number);
        return `periode mulai ${new Intl.DateTimeFormat("id-ID", {
            day: "numeric",
            month: "short",
            year: "numeric",
        }).format(new Date(year, month - 1, day))}`;
    }
    return `bulan ${period}`;
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
    const [activeCategory, setActiveCategory] = useState<string | null>(null);
    const [hoverCategory, setHoverCategory] = useState<string | null>(null);

    const categoryDonut = useMemo(() => {
        const categories = data?.categories;
        if (categories === undefined || categories.length === 0) {
            return null;
        }

        let cumulativePercent = 0;
        return categories.map((item, index) => {
            const percent = Math.min(Math.max(0, item.percent), 100);
            const colorClassName = `category-slice-${index % 6}`;
            const slice = {
                ...item,
                percent,
                offset: -cumulativePercent,
                className: `category-slice ${colorClassName}`,
                colorClassName,
            };
            cumulativePercent += percent;
            return slice;
        });
    }, [data]);

    const maxTrendAmount = useMemo(() => {
        if (!data?.trend.length) {
            return 0;
        }
        return Math.max(
            ...data.trend.map((item) => Math.max(item.income_total, item.expense_total)),
            1,
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
                <h1>Memuat ringkasan...</h1>
                <p className="description">Sedang menghitung ringkasan keuangan kamu.</p>
            </section>
        );
    }

    if (error || !data) {
        return (
            <section className="hero-card dashboard-overview" role="alert">
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
    const selectedCategoryKey = hoverCategory ?? activeCategory;
    const selectedCategory = selectedCategoryKey === null
        ? undefined
        : categoryDonut?.find((item) => item.category === selectedCategoryKey);

    return (
        <section className="hero-card dashboard-overview" aria-labelledby="dashboard-title">
            <h1 id="dashboard-title">Halo {firstName ?? "kamu"}</h1>
            <p className="description">
                Ringkasan {periodLabel(data.summary.month)} berdasarkan transaksi yang kamu catat.
            </p>

            <dl className="summary-grid" aria-label="Ringkasan bulanan">
                <div>
                    <dt>Pemasukan</dt>
                    <dd className="income">{formatRupiah(data.summary.income_total)}</dd>
                </div>
                <div>
                    <dt>Pengeluaran</dt>
                    <dd className="expense">{formatRupiah(data.summary.expense_total)}</dd>
                </div>
                <div>
                    <dt>Cashflow</dt>
                    <dd className={data.summary.net_cashflow >= 0 ? "income" : "expense"}>
                        {formatRupiah(data.summary.net_cashflow)}
                    </dd>
                </div>
                <div>
                    <dt>Rasio surplus</dt>
                    <dd>{data.summary.surplus_rate_percent}%</dd>
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
                    {categoryDonut === null ? (
                        <p className="muted-text">Belum ada pengeluaran bulan ini.</p>
                    ) : (
                        <div className="category-donut-wrap">
                            <svg
                                className={`category-donut${selectedCategory ? " has-active-category" : ""}`}
                                viewBox="0 0 120 120"
                                role="img"
                                aria-labelledby="category-donut-title category-donut-desc"
                                onClick={(event) => {
                                    const target = event.target;
                                    if (
                                        target instanceof SVGCircleElement &&
                                        target.classList.contains("category-slice")
                                    ) {
                                        return;
                                    }
                                    setActiveCategory(null);
                                    setHoverCategory(null);
                                }}
                            >
                                <title id="category-donut-title">Pie chart kategori pengeluaran</title>
                                <desc id="category-donut-desc">
                                    Proporsi pengeluaran berdasarkan kategori.
                                </desc>
                                <circle className="category-donut-track" cx="60" cy="60" r="42" />
                                {categoryDonut.map((item) => {
                                    const label = categoryLabel(item.category);
                                    const isSelected = selectedCategory?.category === item.category;
                                    return (
                                        <circle
                                            key={item.category}
                                            className={`${item.className}${isSelected ? " is-selected" : ""}`}
                                            cx="60"
                                            cy="60"
                                            r="42"
                                            pathLength="100"
                                            role="button"
                                            tabIndex={0}
                                            aria-label={`${label}: ${item.percent}% atau ${formatRupiah(item.amount)}`}
                                            aria-pressed={activeCategory === item.category}
                                            strokeDasharray={`${item.percent} ${100 - item.percent}`}
                                            strokeDashoffset={item.offset}
                                            onBlur={() => setHoverCategory(null)}
                                            onClick={() => setActiveCategory(item.category)}
                                            onFocus={() => setHoverCategory(item.category)}
                                            onMouseEnter={() => setHoverCategory(item.category)}
                                            onMouseLeave={() => setHoverCategory(null)}
                                            onKeyDown={(event) => {
                                                if (event.key === "Enter" || event.key === " ") {
                                                    event.preventDefault();
                                                    setActiveCategory(item.category);
                                                }
                                            }}
                                        />
                                    );
                                })}
                                {selectedCategory ? null : (
                                    <text className="category-donut-label" x="60" y="56">
                                        Total
                                    </text>
                                )}
                                <text
                                    className="category-donut-value"
                                    x="60"
                                    y={selectedCategory ? "66" : "73"}
                                >
                                    {selectedCategory
                                        ? `${selectedCategory.percent}%`
                                        : formatRupiah(data.summary.expense_total)}
                                </text>
                            </svg>
                            {selectedCategory ? (
                                <div className="category-active-detail" role="status">
                                    <span>{categoryLabel(selectedCategory.category)}</span>
                                    <strong>{formatRupiah(selectedCategory.amount)}</strong>
                                    <small>{selectedCategory.percent}% dari pengeluaran</small>
                                </div>
                            ) : null}
                            <ul className="category-legend" aria-label="Daftar kategori pengeluaran">
                                {categoryDonut.map((item) => {
                                    const label = categoryLabel(item.category);
                                    const isSelected = selectedCategory?.category === item.category;
                                    return (
                                        <li key={item.category}>
                                            <button
                                                className={`category-legend-button${isSelected ? " is-selected" : ""}`}
                                                type="button"
                                                onClick={() => setActiveCategory(item.category)}
                                            >
                                                <span
                                                    className={`category-legend-dot ${item.colorClassName}`}
                                                    aria-hidden="true"
                                                />
                                                <span className="category-legend-name">{label}</span>
                                                <strong>{item.percent}%</strong>
                                            </button>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    )}
                </section>

                <section className="dashboard-card" aria-labelledby="trend-title">
                    <h2 id="trend-title">Tren bulanan</h2>
                    <p className="chart-legend" aria-hidden="true">
                        <span className="legend-dot income-dot" /> Pemasukan
                        <span className="legend-dot expense-dot" /> Pengeluaran
                    </p>
                    <ul className="trend-list" aria-label="Tren pemasukan dan pengeluaran">
                        {data.trend.map((item) => (
                            <li key={item.month}>
                                <span>{monthLabel(item.month)}</span>
                                <div className="trend-bars">
                                    <span
                                        className="income-bar"
                                        style={{
                                            width: `${(item.income_total / maxTrendAmount) * 100}%`,
                                        }}
                                    />
                                    <span
                                        className="expense-bar"
                                        style={{
                                            width: `${(item.expense_total / maxTrendAmount) * 100}%`,
                                        }}
                                    />
                                </div>
                                <strong className={item.net_cashflow >= 0 ? "income" : "expense"}>
                                    {formatRupiah(item.net_cashflow)}
                                </strong>
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
                                <strong className={transaction.type === "income" ? "income" : "expense"}>
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
