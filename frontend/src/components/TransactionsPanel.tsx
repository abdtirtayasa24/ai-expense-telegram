import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";

import {
    createTransaction,
    deleteTransaction,
    listTransactions,
    type Transaction,
    type TransactionCategory,
    type TransactionPayload,
    type TransactionType,
    updateTransaction,
} from "../api/transactions";
import { formatRupiah } from "../utils/currency";
import { EditTransactionModal } from "./EditTransactionModal";

const PAGE_SIZE = 10;

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

const DEFAULT_FORM: TransactionPayload = {
    type: "expense",
    name: "",
    category: "transportasi",
    amount: 0,
    transaction_date: new Date().toISOString().slice(0, 10),
    note: "",
};

interface TransactionsPanelProps {
    token: string;
    isActive: boolean;
    refreshKey: number;
    onDataChanged: () => void;
    onUnauthorized: (message: string) => void;
}

function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") {
            return detail;
        }
    }
    return "Transaksi belum bisa dimuat. Coba lagi sebentar.";
}

function categoryLabel(category: string): string {
    return category.replace(/_/g, " ");
}

export function TransactionsPanel({
    token,
    isActive,
    refreshKey,
    onDataChanged,
    onUnauthorized,
}: TransactionsPanelProps) {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [form, setForm] = useState<TransactionPayload>(DEFAULT_FORM);
    const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
    const [offset, setOffset] = useState(0);
    const [hasNext, setHasNext] = useState(false);
    const [lastLoadedRefreshKey, setLastLoadedRefreshKey] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const totalExpense = useMemo(
        () =>
            transactions
                .filter((transaction) => transaction.type === "expense")
                .reduce((total, transaction) => total + transaction.amount, 0),
        [transactions],
    );

    const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

    const loadTransactions = useCallback(
        async (targetOffset = offset, loadedRefreshKey = refreshKey) => {
            setIsLoading(true);
            setError(null);
            try {
                const response = await listTransactions(token, {
                    limit: PAGE_SIZE,
                    offset: targetOffset,
                });
                setTransactions(response.items);
                setOffset(response.offset);
                setHasNext(response.has_next);
                setLastLoadedRefreshKey(loadedRefreshKey);
            } catch (requestError) {
                if (
                    axios.isAxiosError(requestError) &&
                    requestError.response?.status === 401
                ) {
                    onUnauthorized("Sesi kamu sudah berakhir. Silakan buka ulang Mini App.");
                    return;
                }
                setError(errorMessage(requestError));
            } finally {
                setIsLoading(false);
            }
        },
        [offset, onUnauthorized, refreshKey, token],
    );

    useEffect(() => {
        if (!isActive) {
            return;
        }
        if (lastLoadedRefreshKey === refreshKey) {
            return;
        }
        void loadTransactions(0, refreshKey);
    }, [isActive, lastLoadedRefreshKey, loadTransactions, refreshKey]);

    function resetForm() {
        setForm({
            ...DEFAULT_FORM,
            transaction_date: new Date().toISOString().slice(0, 10),
        });
    }

    function handleRequestError(requestError: unknown) {
        if (axios.isAxiosError(requestError) && requestError.response?.status === 401) {
            onUnauthorized("Sesi kamu sudah berakhir. Silakan buka ulang Mini App.");
            return;
        }
        setError(errorMessage(requestError));
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setIsSaving(true);
        setError(null);
        try {
            await createTransaction(token, form);
            resetForm();
            onDataChanged();
            await loadTransactions(0, refreshKey);
        } catch (requestError) {
            handleRequestError(requestError);
        } finally {
            setIsSaving(false);
        }
    }

    async function handleUpdate(payload: TransactionPayload) {
        if (editingTransaction === null) {
            return;
        }
        setIsSaving(true);
        setError(null);
        try {
            await updateTransaction(token, editingTransaction.id, payload);
            setEditingTransaction(null);
            onDataChanged();
            await loadTransactions(offset, refreshKey);
        } catch (requestError) {
            handleRequestError(requestError);
        } finally {
            setIsSaving(false);
        }
    }

    async function handleDelete(transactionId: string) {
        const confirmed = window.confirm("Hapus transaksi ini?");
        if (!confirmed) {
            return;
        }
        setError(null);
        try {
            await deleteTransaction(token, transactionId);
            onDataChanged();
            const targetOffset = transactions.length === 1 && offset > 0
                ? Math.max(0, offset - PAGE_SIZE)
                : offset;
            await loadTransactions(targetOffset, refreshKey);
        } catch (requestError) {
            handleRequestError(requestError);
        }
    }

    async function goToPreviousPage() {
        await loadTransactions(Math.max(0, offset - PAGE_SIZE), refreshKey);
    }

    async function goToNextPage() {
        await loadTransactions(offset + PAGE_SIZE, refreshKey);
    }

    return (
        <section className="transactions-section" aria-labelledby="transactions-title">
            <div className="section-header">
                <div>
                    <p className="eyebrow">Transaksi</p>
                    <h2 id="transactions-title">Catatan manual</h2>
                </div>
                <div className="metric-card" aria-label="Total pengeluaran di halaman ini">
                    <span>Pengeluaran halaman ini</span>
                    <strong>{formatRupiah(totalExpense)}</strong>
                </div>
            </div>

            <form className="transaction-form" onSubmit={handleSubmit}>
                <div className="form-grid">
                    <label>
                        Tipe
                        <select
                            value={form.type}
                            onChange={(event) =>
                                setForm((current) => ({
                                    ...current,
                                    type: event.target.value as TransactionType,
                                }))
                            }
                        >
                            <option value="expense">Pengeluaran</option>
                            <option value="income">Pemasukan</option>
                        </select>
                    </label>
                    <label>
                        Nama
                        <input
                            required
                            value={form.name}
                            onChange={(event) =>
                                setForm((current) => ({ ...current, name: event.target.value }))
                            }
                            placeholder="Contoh: Parkir kantor"
                        />
                    </label>
                    <label>
                        Kategori
                        <select
                            value={form.category}
                            onChange={(event) =>
                                setForm((current) => ({
                                    ...current,
                                    category: event.target.value as TransactionCategory,
                                }))
                            }
                        >
                            {CATEGORIES.map((category) => (
                                <option key={category.value} value={category.value}>
                                    {category.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        Nominal
                        <input
                            required
                            min="1"
                            type="number"
                            inputMode="numeric"
                            value={form.amount || ""}
                            onChange={(event) =>
                                setForm((current) => ({
                                    ...current,
                                    amount: Number(event.target.value),
                                }))
                            }
                            placeholder="5000"
                        />
                    </label>
                    <label>
                        Tanggal
                        <input
                            required
                            type="date"
                            value={form.transaction_date}
                            onChange={(event) =>
                                setForm((current) => ({
                                    ...current,
                                    transaction_date: event.target.value,
                                }))
                            }
                        />
                    </label>
                    <label>
                        Catatan
                        <input
                            value={form.note ?? ""}
                            onChange={(event) =>
                                setForm((current) => ({ ...current, note: event.target.value }))
                            }
                            placeholder="Opsional"
                        />
                    </label>
                </div>
                <div className="form-actions">
                    <button className="primary-button" disabled={isSaving} type="submit">
                        {isSaving ? "Menyimpan..." : "Tambah transaksi"}
                    </button>
                </div>
            </form>

            {error ? <p className="inline-error" role="alert">{error}</p> : null}

            {isLoading ? (
                <div className="list-state" aria-busy="true">
                    Memuat transaksi...
                </div>
            ) : transactions.length === 0 ? (
                <div className="list-state" role="status">
                    Belum ada transaksi. Tambahkan transaksi pertama kamu dari formulir di atas.
                </div>
            ) : (
                <>
                    <ul className="transaction-list compact" aria-label="Daftar transaksi">
                        {transactions.map((transaction) => (
                            <li className="transaction-item" key={transaction.id}>
                                <div className="transaction-main">
                                    <strong>{transaction.name}</strong>
                                    <span className="transaction-meta">
                                        {transaction.type === "income" ? "Pemasukan" : "Pengeluaran"} · {categoryLabel(transaction.category)} · {transaction.transaction_date}
                                    </span>
                                </div>
                                <div className="transaction-actions">
                                    <span className={transaction.type === "income" ? "income" : "expense"}>
                                        {transaction.type === "income" ? "+" : "-"}
                                        {formatRupiah(transaction.amount)}
                                    </span>
                                    <button
                                        type="button"
                                        className="secondary-button small"
                                        onClick={() => setEditingTransaction(transaction)}
                                    >
                                        Edit
                                    </button>
                                    <button
                                        type="button"
                                        className="danger-button small"
                                        onClick={() => void handleDelete(transaction.id)}
                                    >
                                        Hapus
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                    <nav className="pagination-controls" aria-label="Paginasi transaksi">
                        <button
                            type="button"
                            className="secondary-button small"
                            disabled={offset === 0 || isLoading}
                            onClick={() => void goToPreviousPage()}
                        >
                            Sebelumnya
                        </button>
                        <span>Halaman {currentPage}</span>
                        <button
                            type="button"
                            className="secondary-button small"
                            disabled={!hasNext || isLoading}
                            onClick={() => void goToNextPage()}
                        >
                            Berikutnya
                        </button>
                    </nav>
                </>
            )}

            {editingTransaction ? (
                <EditTransactionModal
                    transaction={editingTransaction}
                    categories={CATEGORIES}
                    isSaving={isSaving}
                    onClose={() => setEditingTransaction(null)}
                    onSave={(payload) => void handleUpdate(payload)}
                />
            ) : null}
        </section>
    );
}
