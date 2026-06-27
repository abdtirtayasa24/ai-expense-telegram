import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export type TransactionType = "income" | "expense";

export type TransactionCategory =
    | "transportasi"
    | "makanan_minuman"
    | "tagihan"
    | "tempat_tinggal"
    | "belanja"
    | "hiburan"
    | "utang_cicilan"
    | "pendapatan"
    | "kesehatan"
    | "pendidikan"
    | "keluarga"
    | "lainnya";

export interface Transaction {
    id: string;
    type: TransactionType;
    name: string;
    category: TransactionCategory;
    amount: number;
    transaction_date: string;
    note: string | null;
    source: "telegram_chat" | "manual";
    parser: "rule_based" | "gemini" | "manual";
    confidence_score: number | null;
}

export interface TransactionPayload {
    type: TransactionType;
    name: string;
    category: TransactionCategory;
    amount: number;
    transaction_date: string;
    note?: string | null;
}

export interface TransactionListResponse {
    items: Transaction[];
    limit: number;
    offset: number;
}

function authHeaders(token: string) {
    return {
        Authorization: `Bearer ${token}`,
    };
}

export async function listTransactions(token: string): Promise<Transaction[]> {
    const response = await axios.get<TransactionListResponse>(`${API_BASE_URL}/transactions`, {
        headers: authHeaders(token),
    });
    return response.data.items;
}

export async function createTransaction(
    token: string,
    payload: TransactionPayload,
): Promise<Transaction> {
    const response = await axios.post<Transaction>(`${API_BASE_URL}/transactions`, payload, {
        headers: authHeaders(token),
    });
    return response.data;
}

export async function updateTransaction(
    token: string,
    transactionId: string,
    payload: Partial<TransactionPayload>,
): Promise<Transaction> {
    const response = await axios.patch<Transaction>(
        `${API_BASE_URL}/transactions/${transactionId}`,
        payload,
        { headers: authHeaders(token) },
    );
    return response.data;
}

export async function deleteTransaction(
    token: string,
    transactionId: string,
): Promise<void> {
    await axios.delete(`${API_BASE_URL}/transactions/${transactionId}`, {
        headers: authHeaders(token),
    });
}
