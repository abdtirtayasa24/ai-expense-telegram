import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export interface AuthenticatedUser {
    id: string;
    telegram_user_id: number;
    first_name: string | null;
    last_name: string | null;
    role: string;
    status: string;
    currency: string;
    timezone: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: "bearer";
    user: AuthenticatedUser;
}

export async function loginWithTelegramMiniApp(): Promise<AuthResponse> {
    const initData = window.Telegram?.WebApp?.initData;

    if (!initData) {
        throw new Error("Telegram initData tidak ditemukan.");
    }

    const response = await axios.post<AuthResponse>(
        `${API_BASE_URL}/auth/telegram-mini-app`,
        {
            init_data: initData,
        },
    );

    return response.data;
}
