import axios from "axios";

import { getApiBaseUrl } from "./config";

const API_BASE_URL = getApiBaseUrl();

export interface UserSettings {
    cashflow_period_start_day: number;
}

function authHeaders(token: string) {
    return {
        Authorization: `Bearer ${token}`,
    };
}

export async function getSettings(token: string): Promise<UserSettings> {
    const response = await axios.get<UserSettings>(`${API_BASE_URL}/settings`, {
        headers: authHeaders(token),
    });
    return response.data;
}

export async function updateCashflowPeriod(
    token: string,
    cashflowPeriodStartDay: number,
): Promise<UserSettings> {
    const response = await axios.patch<UserSettings>(
        `${API_BASE_URL}/settings/cashflow-period`,
        { cashflow_period_start_day: cashflowPeriodStartDay },
        { headers: authHeaders(token) },
    );
    return response.data;
}
