import axios from "axios";

import { getApiBaseUrl } from "./config";

const API_BASE_URL = getApiBaseUrl();

export interface InsightsResponse {
    summary: string;
    recommendations: string[];
    warnings: string[];
}

export interface ChatResponse {
    answer: string;
}

function authHeaders(token: string) {
    return {
        Authorization: `Bearer ${token}`,
    };
}

export async function getInsights(token: string): Promise<InsightsResponse> {
    const response = await axios.post<InsightsResponse>(
        `${API_BASE_URL}/advisor/insights`,
        {},
        { headers: authHeaders(token) },
    );
    return response.data;
}

export async function sendChatMessage(
    token: string,
    message: string,
): Promise<ChatResponse> {
    const response = await axios.post<ChatResponse>(
        `${API_BASE_URL}/advisor/chat`,
        { message },
        { headers: authHeaders(token) },
    );
    return response.data;
}
