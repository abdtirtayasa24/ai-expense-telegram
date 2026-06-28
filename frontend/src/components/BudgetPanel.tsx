import { type FormEvent, useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
    createBudget,
    deleteBudget,
    listBudgets,
    updateBudget,
    type Budget,
} from "../api/budgets";
import type { TransactionCategory } from "../api/transactions";
import { formatRupiah } from "../utils/currency";

const CATEGORIES: { value: TransactionCategory; label: string }[] = [
    { value: "transportasi", label: "Transportasi" },
    { value: "makanan_minuman", label: "Makanan & minuman" },
    { value: "tagihan", label: "Tagihan" },
    { value: "tempat_tinggal", label: "Tempat tinggal" },
    { value: "belanja", label: "Belanja" },
    { value: "hiburan", label: "Hiburan" },
    { value: "utang_cicilan", label: "Utang/cicilan" },
    { value: "pendapatan", label: "Pendapatan" },
    { value: "kesehatan", label: "Kesehatan" },
    { value: "pendidikan", label: "Pendidikan" },
    { value: "keluarga", label: "Keluarga" },
    { value: "lainnya", label: "Lainnya" },
];

interface BudgetPanelProps {
    token: string;
    isActive: boolean;
    refreshKey: number;
    onDataChanged: () => void;
    onUnauthorized: (message: string) => void;
}

function currentMonth(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") {
            return detail;
        }
    }
    return "Budget belum bisa dimuat.";
}

function categoryLabel(category: string): string {
    return category.replace(/_/g, " ");
}

export function BudgetPanel({
    token,
    isActive,
    refreshKey,
    onDataChanged,
    onUnauthorized,
}: BudgetPanelProps) {
    const [budgets, setBudgets] = useState<Budget[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastLoadedRefreshKey, setLastLoadedRefreshKey] = useState<number | null>(null);
    const [form, setForm] = useState({
        category: "transportasi" as TransactionCategory,
        monthly_limit: 0,
    });
    const [editingId, setEditingId] = useState<string | null>(null);

    const loadBudgets = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            setBudgets(await listBudgets(token));
            setLastLoadedRefreshKey(refreshKey);
        } catch (requestError) {
            if (axios.isAxiosError(requestError) && requestError.response?.status === 401) {
                onUnauthorized("Sesi kamu sudah berakhir.");
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
        void loadBudgets();
    }, [isActive, lastLoadedRefreshKey, loadBudgets, refreshKey]);

    function resetForm() {
        setEditingId(null);
        setForm({ category: "transportasi", monthly_limit: 0 });
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setIsSaving(true);
        setError(null);
        try {
            if (editingId) {
                const updated = await updateBudget(token, editingId, {
                    monthly_limit: form.monthly_limit,
                });
                setBudgets((current) =>
                    current.map((b) => (b.id === updated.id ? updated : b)),
                );
                onDataChanged();
            } else {
                const created = await createBudget(token, {
                    ...form,
                    month: currentMonth(),
                });
                setBudgets((current) => [created, ...current]);
                onDataChanged();
            }
            resetForm();
        } catch (requestError) {
            setError(errorMessage(requestError));
        } finally {
            setIsSaving(false);
        }
    }

    async function handleDelete(budgetId: string) {
        const confirmed = window.confirm("Hapus budget ini?");
        if (!confirmed) return;
        setError(null);
        try {
            await deleteBudget(token, budgetId);
            setBudgets((current) => current.filter((b) => b.id !== budgetId));
            onDataChanged();
        } catch (requestError) {
            setError(errorMessage(requestError));
        }
    }

    return (
        <section className="transactions-section" aria-labelledby="budgets-title">
            <div className="section-header">
                <div>
                    <p className="eyebrow">Budget</p>
                    <h2 id="budgets-title">Batas pengeluaran bulanan</h2>
                </div>
            </div>

            <form className="transaction-form" onSubmit={handleSubmit}>
                <div className="form-grid">
                    <label>
                        Kategori
                        <select
                            value={form.category}
                            disabled={editingId !== null}
                            onChange={(event) =>
                                setForm((current) => ({
                                    ...current,
                                    category: event.target.value as TransactionCategory,
                                }))
                            }
                        >
                            {CATEGORIES.map((c) => (
                                <option key={c.value} value={c.value}>
                                    {c.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        Batas bulanan
                        <input
                            required
                            min="1"
                            type="number"
                            inputMode="numeric"
                            value={form.monthly_limit || ""}
                            onChange={(event) =>
                                setForm((current) => ({
                                    ...current,
                                    monthly_limit: Number(event.target.value),
                                }))
                            }
                            placeholder="100000"
                        />
                    </label>
                </div>
                <div className="form-actions">
                    {editingId ? (
                        <button
                            type="button"
                            className="secondary-button"
                            onClick={resetForm}
                        >
                            Batal
                        </button>
                    ) : null}
                    <button className="primary-button" disabled={isSaving} type="submit">
                        {isSaving
                            ? "Menyimpan..."
                            : editingId
                              ? "Simpan perubahan"
                              : "Tambah budget"}
                    </button>
                </div>
            </form>

            {error ? (
                <p className="inline-error" role="alert">
                    {error}
                </p>
            ) : null}

            {isLoading ? (
                <div className="list-state" aria-busy="true">
                    Memuat budget...
                </div>
            ) : budgets.length === 0 ? (
                <div className="list-state" role="status">
                    Belum ada budget. Tambahkan budget pertama dari formulir di atas.
                </div>
            ) : (
                <ul className="transaction-list" aria-label="Daftar budget">
                    {budgets.map((budget) => {
                        const isOver = budget.remaining < 0;
                        return (
                            <li
                                className={`transaction-item${isOver ? " over-budget" : ""}`}
                                key={budget.id}
                            >
                                <div>
                                    <strong>{categoryLabel(budget.category)}</strong>
                                    <span>
                                        Batas {formatRupiah(budget.monthly_limit)} · Terpakai{" "}
                                        {formatRupiah(budget.actual)} · Sisa{" "}
                                        {formatRupiah(budget.remaining)}
                                    </span>
                                </div>
                                <div className="transaction-actions">
                                    <span
                                        className={
                                            isOver ? "expense" : "income"
                                        }
                                    >
                                        {budget.percent_used}%
                                    </span>
                                    <button
                                        type="button"
                                        className="secondary-button small"
                                        onClick={() => {
                                            setEditingId(budget.id);
                                            setForm({
                                                category: budget.category,
                                                monthly_limit: budget.monthly_limit,
                                            });
                                        }}
                                    >
                                        Edit
                                    </button>
                                    <button
                                        type="button"
                                        className="danger-button small"
                                        onClick={() => void handleDelete(budget.id)}
                                    >
                                        Hapus
                                    </button>
                                </div>
                            </li>
                        );
                    })}
                </ul>
            )}
        </section>
    );
}
