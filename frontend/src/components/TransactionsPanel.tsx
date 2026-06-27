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

function toForm(transaction: Transaction): TransactionPayload {
    return {
        type: transaction.type,
        name: transaction.name,
        category: transaction.category,
        amount: transaction.amount,
        transaction_date: transaction.transaction_date,
        note: transaction.note ?? "",
    };
}

export function TransactionsPanel({ token, onUnauthorized }: TransactionsPanelProps) {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [form, setForm] = useState<TransactionPayload>(DEFAULT_FORM);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const totalExpense = useMemo(
        () =>
            transactions
                .filter((transaction) => transaction.type === "expense")
                .reduce((total, transaction) => total + transaction.amount, 0),
        [transactions],
    );

    const loadTransactions = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            setTransactions(await listTransactions(token));
        } catch (requestError) {
            if (axios.isAxiosError(requestError) && requestError.response?.status === 401) {
                onUnauthorized("Sesi kamu sudah berakhir. Silakan buka ulang Mini App.");
                return;
            }
            setError(errorMessage(requestError));
        } finally {
            setIsLoading(false);
        }
    }, [onUnauthorized, token]);

    useEffect(() => {
        void loadTransactions();
    }, [loadTransactions]);

    function resetForm() {
        setEditingId(null);
        setForm(DEFAULT_FORM);
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setIsSaving(true);
        setError(null);
        try {
            if (editingId) {
                const updated = await updateTransaction(token, editingId, form);
                setTransactions((current) =>
                    current.map((transaction) =>
                        transaction.id === updated.id ? updated : transaction,
                    ),
                );
            } else {
                const created = await createTransaction(token, form);
                setTransactions((current) => [created, ...current]);
            }
            resetForm();
        } catch (requestError) {
            setError(errorMessage(requestError));
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
            setTransactions((current) =>
                current.filter((transaction) => transaction.id !== transactionId),
            );
        } catch (requestError) {
            setError(errorMessage(requestError));
        }
    }

    return (
        <section className="transactions-section" aria-labelledby="transactions-title">
            <div className="section-header">
                <div>
                    <p className="eyebrow">Transaksi</p>
                    <h2 id="transactions-title">Catatan manual</h2>
                </div>
                <div className="metric-card" aria-label="Total pengeluaran terlihat">
                    <span>Total pengeluaran</span>
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
                    {editingId ? (
                        <button type="button" className="secondary-button" onClick={resetForm}>
                            Batal
                        </button>
                    ) : null}
                    <button className="primary-button" disabled={isSaving} type="submit">
                        {isSaving ? "Menyimpan..." : editingId ? "Simpan perubahan" : "Tambah transaksi"}
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
                <ul className="transaction-list" aria-label="Daftar transaksi">
                    {transactions.map((transaction) => (
                        <li className="transaction-item" key={transaction.id}>
                            <div>
                                <strong>{transaction.name}</strong>
                                <span>
                                    {transaction.type === "income" ? "Pemasukan" : "Pengeluaran"} · {transaction.category} · {transaction.transaction_date}
                                </span>
                            </div>
                            <div className="transaction-actions">
                                <span className={transaction.type === "income" ? "income" : "expense"}>
                                    {formatRupiah(transaction.amount)}
                                </span>
                                <button
                                    type="button"
                                    className="secondary-button small"
                                    onClick={() => {
                                        setEditingId(transaction.id);
                                        setForm(toForm(transaction));
                                    }}
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
            )}
        </section>
    );
}
