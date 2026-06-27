export function getApiBaseUrl(): string {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

    if (!apiBaseUrl) {
        throw new Error(
            "Frontend API base URL is not configured. Set VITE_API_BASE_URL before building the app.",
        );
    }

    return apiBaseUrl.replace(/\/$/, "");
}
