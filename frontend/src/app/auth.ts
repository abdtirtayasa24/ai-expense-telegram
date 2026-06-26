import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function loginWithTelegramMiniApp() {
    const initData = window.Telegram?.WebApp?.initData;

    if (!initData) {
        throw new Error("Telegram initData not found.");
    }

    const response = await axios.post(`${API_BASE_URL}/auth/telegram-mini-app`, {
        init_data: initData,
    });

    return response.data;
}