import { type FormEvent, useEffect, useRef, useState } from "react";

import type {
    Transaction,
    TransactionCategory,
    TransactionPayload,
    TransactionType,
} from "../api/transactions";

interface CategoryOption {
    value: TransactionCategory;
    label: string;
}

interface EditTransactionModalProps {
    transaction: Transaction | null;
    categories: CategoryOption[];
    isSaving: boolean;
    onClose: () => void;
    onSave: (payload: TransactionPayload) => void;
}

const DEFAULT_FORM: TransactionPayload = {
    type: "expense",
    name: "",
    category: "transportasi",
    amount: 0,
    transaction_date: new Date().toISOString().slice(0, 10),
    note: "",
};

function toForm(transaction: Transaction | null): TransactionPayload {
    if (transaction === null) {
        return {
            ...DEFAULT_FORM,
            transaction_date: new Date().toISOString().slice(0, 10),
        };
    }

    return {
        type: transaction.type,
        name: transaction.name,
        category: transaction.category,
        amount: transaction.amount,
        transaction_date: transaction.transaction_date,
        note: transaction.note ?? "",
    };
}

export function EditTransactionModal({
    transaction,
    categories,
    isSaving,
    onClose,
    onSave,
}: EditTransactionModalProps) {
    const [form, setForm] = useState<TransactionPayload>(() => toForm(transaction));
    const closeButtonRef = useRef<HTMLButtonElement>(null);
    const modalRef = useRef<HTMLElement>(null);

    useEffect(() => {
        setForm(toForm(transaction));
    }, [transaction]);

    useEffect(() => {
        closeButtonRef.current?.focus();
    }, []);

    useEffect(() => {
        function focusableElements(): HTMLElement[] {
            if (modalRef.current === null) {
                return [];
            }
            return Array.from(
                modalRef.current.querySelectorAll<HTMLElement>(
                    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
                ),
            );
        }

        function handleKeyDown(event: KeyboardEvent) {
            if (event.key === "Escape") {
                onClose();
                return;
            }

            if (event.key !== "Tab") {
                return;
            }

            const elements = focusableElements();
            if (elements.length === 0) {
                return;
            }

            const firstElement = elements[0];
            const lastElement = elements[elements.length - 1];
            if (event.shiftKey && document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
                return;
            }
            if (!event.shiftKey && document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [onClose]);

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        onSave(form);
    }

    const title = transaction === null ? "Tambah transaksi" : "Edit transaksi";
    const description = transaction === null
        ? "Catat pemasukan atau pengeluaran manual tanpa meninggalkan halaman."
        : "Perbarui detail transaksi tanpa meninggalkan halaman.";

    return (
        <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
            <section
                ref={modalRef}
                className="modal-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby="transaction-modal-title"
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="modal-header">
                    <div>
                        <h2 id="transaction-modal-title">{title}</h2>
                        <p className="section-description">{description}</p>
                    </div>
                    <button
                        ref={closeButtonRef}
                        className="secondary-button small"
                        type="button"
                        onClick={onClose}
                    >
                        Tutup
                    </button>
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
                                    setForm((current) => ({
                                        ...current,
                                        name: event.target.value,
                                    }))
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
                                {categories.map((category) => (
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
                                placeholder="Contoh: 5000"
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
                                    setForm((current) => ({
                                        ...current,
                                        note: event.target.value,
                                    }))
                                }
                                placeholder="Opsional"
                            />
                        </label>
                    </div>
                    <div className="form-actions">
                        <button
                            type="button"
                            className="secondary-button"
                            onClick={onClose}
                        >
                            Batal
                        </button>
                        <button className="primary-button" disabled={isSaving} type="submit">
                            {isSaving ? "Menyimpan..." : "Simpan"}
                        </button>
                    </div>
                </form>
            </section>
        </div>
    );
}
