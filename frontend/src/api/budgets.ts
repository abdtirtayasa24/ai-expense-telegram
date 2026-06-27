import axios from "axios";

import type { TransactionCategory } from "./transactions";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export interface Budget {
    id: string;
    category: TransactionCategory;
    monthly_limit: number;
    month: string;
    actual: number;
    remaining: number;
    percent_used: number;
}

export interface BudgetListResponse {
    items: Budget[];
}

function authHeaders(token: string) {
    return {
        Authorization: `Bearer ${token}`,
    };
}

export async function listBudgets(token: string): Promise<Budget[]> {
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const response = await axios.get<BudgetListResponse>(
        `${API_BASE_URL}/budgets?month=${month}`,
        { headers: authHeaders(token) },
    );
    return response.data.items;
}

export async function createBudget(
    token: string,
    payload: {
        category: TransactionCategory;
        monthly_limit: number;
        month: string;
    },
): Promise<Budget> {
    const response = await axios.post<Budget>(
        `${API_BASE_URL}/budgets`,
        payload,
        { headers: authHeaders(token) },
    );
    return response.data;
}

export async function updateBudget(
    token: string,
    budgetId: string,
    payload: { monthly_limit: number },
): Promise<Budget> {
    const response = await axios.patch<Budget>(
        `${API_BASE_URL}/budgets/${budgetId}`,
        payload,
        { headers: authHeaders(token) },
    );
    return response.data;
}

export async function deleteBudget(
    token: string,
    budgetId: string,
): Promise<void> {
    await axios.delete(`${API_BASE_URL}/budgets/${budgetId}`, {
        headers: authHeaders(token),
    });
}
