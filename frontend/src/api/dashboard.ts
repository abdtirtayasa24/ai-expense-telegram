import axios from "axios";

import { getApiBaseUrl } from "./config";
import type { Transaction } from "./transactions";

const API_BASE_URL = getApiBaseUrl();

export interface DashboardSummary {
    month: string;
    income_total: number;
    expense_total: number;
    net_cashflow: number;
    savings_rate_percent: number;
}

export interface CategoryBreakdownItem {
    category: string;
    amount: number;
    percent: number;
}

export interface CategoryBreakdownResponse {
    items: CategoryBreakdownItem[];
}

export interface TrendItem {
    month: string;
    income_total: number;
    expense_total: number;
    net_cashflow: number;
}

export interface TrendResponse {
    items: TrendItem[];
}

export interface RecentTransactionsResponse {
    items: Transaction[];
}

function authHeaders(token: string) {
    return {
        Authorization: `Bearer ${token}`,
    };
}

export async function getDashboardSummary(token: string): Promise<DashboardSummary> {
    const response = await axios.get<DashboardSummary>(`${API_BASE_URL}/dashboard/summary`, {
        headers: authHeaders(token),
    });
    return response.data;
}

export async function getCategoryBreakdown(
    token: string,
): Promise<CategoryBreakdownItem[]> {
    const response = await axios.get<CategoryBreakdownResponse>(
        `${API_BASE_URL}/dashboard/categories`,
        { headers: authHeaders(token) },
    );
    return response.data.items;
}

export async function getMonthlyTrend(token: string): Promise<TrendItem[]> {
    const response = await axios.get<TrendResponse>(`${API_BASE_URL}/dashboard/trend`, {
        headers: authHeaders(token),
    });
    return response.data.items;
}

export async function getRecentTransactions(token: string): Promise<Transaction[]> {
    const response = await axios.get<RecentTransactionsResponse>(
        `${API_BASE_URL}/dashboard/recent-transactions`,
        { headers: authHeaders(token) },
    );
    return response.data.items;
}
