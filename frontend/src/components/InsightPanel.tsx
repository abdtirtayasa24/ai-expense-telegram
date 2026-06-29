import { type FormEvent, type ReactNode, useCallback, useEffect, useState } from "react";
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

type AdvisorTextBlock =
    | { type: "paragraph"; text: string }
    | { type: "unordered-list"; items: string[] }
    | { type: "ordered-list"; items: string[] };

function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") {
            return detail;
        }
    }
    return "Insight belum bisa dimuat. Coba lagi sebentar.";
}

function parseAdvisorText(text: string): AdvisorTextBlock[] {
    const blocks: AdvisorTextBlock[] = [];
    let paragraphLines: string[] = [];
    let listBlock: Extract<AdvisorTextBlock, { items: string[] }> | null = null;

    const flushParagraph = () => {
        if (paragraphLines.length === 0) {
            return;
        }
        blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
        paragraphLines = [];
    };

    const flushList = () => {
        if (listBlock === null) {
            return;
        }
        blocks.push(listBlock);
        listBlock = null;
    };

    for (const rawLine of text.replace(/\r\n/g, "\n").split("\n")) {
        const line = rawLine.trim();
        if (!line) {
            flushParagraph();
            flushList();
            continue;
        }

        const unorderedMatch = line.match(/^[-*•]\s+(.+)$/);
        const orderedMatch = line.match(/^\d+[.)]\s+(.+)$/);

        if (unorderedMatch !== null) {
            flushParagraph();
            if (listBlock?.type !== "unordered-list") {
                flushList();
                listBlock = { type: "unordered-list", items: [] };
            }
            listBlock.items.push(unorderedMatch[1]);
            continue;
        }

        if (orderedMatch !== null) {
            flushParagraph();
            if (listBlock?.type !== "ordered-list") {
                flushList();
                listBlock = { type: "ordered-list", items: [] };
            }
            listBlock.items.push(orderedMatch[1]);
            continue;
        }

        flushList();
        paragraphLines.push(line);
    }

    flushParagraph();
    flushList();

    return blocks.length > 0 ? blocks : [{ type: "paragraph", text }];
}

function renderInlineText(text: string): ReactNode[] {
    return text
        .split(/(\*\*[^*]+\*\*)/g)
        .filter(Boolean)
        .map((segment, index) => {
            if (segment.startsWith("**") && segment.endsWith("**")) {
                return <strong key={index}>{segment.slice(2, -2)}</strong>;
            }
            return segment;
        });
}

function FormattedAdvisorText({ text }: { text: string }) {
    return parseAdvisorText(text).map((block, index) => {
        if (block.type === "unordered-list") {
            return (
                <ul key={index}>
                    {block.items.map((item, itemIndex) => (
                        <li key={itemIndex}>{renderInlineText(item)}</li>
                    ))}
                </ul>
            );
        }

        if (block.type === "ordered-list") {
            return (
                <ol key={index}>
                    {block.items.map((item, itemIndex) => (
                        <li key={itemIndex}>{renderInlineText(item)}</li>
                    ))}
                </ol>
            );
        }

        return <p key={index}>{renderInlineText(block.text)}</p>;
    });
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
            if (
                axios.isAxiosError(requestError) &&
                requestError.response?.status === 401
            ) {
                onUnauthorized("Sesi kamu sudah berakhir.");
                return;
            }
            setError(errorMessage(requestError));
        } finally {
            setIsSending(false);
        }
    }

    return (
        <section className="transactions-section" aria-labelledby="insights-title">
            <div className="section-header">
                <div>
                    <h2 id="insights-title">Insight keuangan</h2>
                    <p className="section-description">
                        Dapatkan ringkasan dan tanya saran cashflow berdasarkan data kamu.
                    </p>
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
                <div className="list-state state-with-action" role="alert">
                    <span>{error}</span>
                    <button
                        className="secondary-button small"
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
                                {msg.role === "user" ? (
                                    <span className="chat-bubble">{msg.text}</span>
                                ) : (
                                    <div className="chat-bubble advisor-formatted-text">
                                        <FormattedAdvisorText text={msg.text} />
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="muted-text chat-empty">
                        Mulai dengan pertanyaan praktis, misalnya cashflow bulan ini atau
                        kategori yang perlu ditekan.
                    </p>
                )}
                <form className="chat-form" onSubmit={handleChatSubmit}>
                    <input
                        aria-label="Pertanyaan untuk AI Advisor"
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
                        {isSending ? "Mengirim" : "Kirim"}
                    </button>
                </form>
            </section>
        </section>
    );
}
