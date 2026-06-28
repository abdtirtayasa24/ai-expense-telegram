import { type FormEvent, useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
    getInsights,
    sendChatMessage,
    type InsightsResponse,
} from "../api/advisor";

interface InsightPanelProps {
    token: string;
    isActive: boolean;
    refreshKey: number;
    onUnauthorized: (message: string) => void;
}

function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") {
            return detail;
        }
    }
    return "Insight belum bisa dimuat. Coba lagi sebentar.";
}

export function InsightPanel({
    token,
    isActive,
    refreshKey,
    onUnauthorized,
}: InsightPanelProps) {
    const [insight, setInsight] = useState<InsightsResponse | null>(null);
    const [chatMessage, setChatMessage] = useState("");
    const [chatHistory, setChatHistory] = useState<
        { role: "user" | "assistant"; text: string }[]
    >([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastLoadedRefreshKey, setLastLoadedRefreshKey] = useState<number | null>(null);

    const loadInsight = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            setInsight(await getInsights(token));
            setLastLoadedRefreshKey(refreshKey);
        } catch (requestError) {
            if (
                axios.isAxiosError(requestError) &&
                requestError.response?.status === 401
            ) {
                onUnauthorized("Sesi kamu sudah berakhir.");
                return;
            }
            setError(errorMessage(requestError));
        } finally {
            setIsLoading(false);
        }
    }, [onUnauthorized, refreshKey, token]);

    useEffect(() => {
        if (!isActive) {
            return;
        }
        if (lastLoadedRefreshKey === refreshKey) {
            return;
        }
        void loadInsight();
    }, [isActive, lastLoadedRefreshKey, loadInsight, refreshKey]);

    async function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const msg = chatMessage.trim();
        if (!msg) return;
        setChatMessage("");
        setChatHistory((prev) => [...prev, { role: "user", text: msg }]);
        setIsSending(true);
        try {
            const response = await sendChatMessage(token, msg);
            setChatHistory((prev) => [
                ...prev,
                { role: "assistant", text: response.answer },
            ]);
        } catch (requestError) {
            setError(errorMessage(requestError));
        } finally {
            setIsSending(false);
        }
    }

    return (
        <section className="transactions-section" aria-labelledby="insights-title">
            <div className="section-header">
                <div>
                    <p className="eyebrow">AI Advisor</p>
                    <h2 id="insights-title">Insight keuangan</h2>
                </div>
            </div>

            {isLoading ? (
                <div className="list-state" aria-busy="true">
                    Sedang membuat insight...
                </div>
            ) : insight && !error ? (
                <div className="dashboard-grid">
                    <section
                        className="dashboard-card"
                        aria-labelledby="summary-title"
                    >
                        <h2 id="summary-title">Ringkasan</h2>
                        <p className="muted-text">{insight.summary}</p>
                    </section>
                    <section
                        className="dashboard-card"
                        aria-labelledby="recommendations-title"
                    >
                        <h2 id="recommendations-title">Rekomendasi</h2>
                        {insight.recommendations.length === 0 ? (
                            <p className="muted-text">
                                Tidak ada rekomendasi khusus.
                            </p>
                        ) : (
                            <ul className="simple-list">
                                {insight.recommendations.map((r, i) => (
                                    <li key={i}>{r}</li>
                                ))}
                            </ul>
                        )}
                    </section>
                    <section
                        className="dashboard-card"
                        aria-labelledby="warnings-title"
                    >
                        <h2 id="warnings-title">Peringatan</h2>
                        {insight.warnings.length === 0 ? (
                            <p className="muted-text">
                                Tidak ada peringatan.
                            </p>
                        ) : (
                            <ul className="simple-list">
                                {insight.warnings.map((w, i) => (
                                    <li key={i}>{w}</li>
                                ))}
                            </ul>
                        )}
                    </section>
                </div>
            ) : error ? (
                <div className="list-state" role="alert">
                    {error}
                    <button
                        className="secondary-button small"
                        style={{ marginLeft: 12 }}
                        type="button"
                        onClick={() => void loadInsight()}
                    >
                        Coba lagi
                    </button>
                </div>
            ) : null}

            <section
                className="dashboard-card recent-card"
                aria-labelledby="chat-title"
            >
                <h2 id="chat-title">Tanya AI Advisor</h2>
                {chatHistory.length > 0 ? (
                    <ul className="chat-history" aria-label="Riwayat chat">
                        {chatHistory.map((msg, i) => (
                            <li
                                key={i}
                                className={
                                    msg.role === "user"
                                        ? "chat-user"
                                        : "chat-assistant"
                                }
                            >
                                <span>{msg.text}</span>
                            </li>
                        ))}
                    </ul>
                ) : null}
                <form className="chat-form" onSubmit={handleChatSubmit}>
                    <input
                        value={chatMessage}
                        onChange={(event) => setChatMessage(event.target.value)}
                        placeholder="Contoh: Bagaimana cashflow saya bulan ini?"
                        disabled={isSending}
                    />
                    <button
                        className="primary-button"
                        disabled={isSending || !chatMessage.trim()}
                        type="submit"
                    >
                        {isSending ? "..." : "Kirim"}
                    </button>
                </form>
            </section>
        </section>
    );
}
