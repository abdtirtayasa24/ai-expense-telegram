import { type FormEvent, useCallback, useEffect, useState } from "react";
import axios from "axios";

import {
    getSettings,
    updateCashflowPeriod,
    type UserSettings,
} from "../api/settings";

interface SettingsPanelProps {
    token: string;
    isActive: boolean;
    refreshKey: number;
    onCashflowPeriodChanged: (startDay: number) => void;
    onUnauthorized: (message: string) => void;
}

function errorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") {
            return detail;
        }
    }
    return "Pengaturan belum bisa dimuat. Coba lagi sebentar.";
}

export function SettingsPanel({
    token,
    isActive,
    refreshKey,
    onCashflowPeriodChanged,
    onUnauthorized,
}: SettingsPanelProps) {
    const [settings, setSettings] = useState<UserSettings | null>(null);
    const [cashflowStartDay, setCashflowStartDay] = useState(1);
    const [lastLoadedRefreshKey, setLastLoadedRefreshKey] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const loadSettings = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await getSettings(token);
            setSettings(response);
            setCashflowStartDay(response.cashflow_period_start_day);
            setLastLoadedRefreshKey(refreshKey);
        } catch (requestError) {
            if (axios.isAxiosError(requestError) && requestError.response?.status === 401) {
                onUnauthorized("Sesi kamu sudah berakhir. Silakan buka ulang Mini App.");
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
        void loadSettings();
    }, [isActive, lastLoadedRefreshKey, loadSettings, refreshKey]);

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setIsSaving(true);
        setError(null);
        setMessage(null);
        try {
            const response = await updateCashflowPeriod(token, cashflowStartDay);
            setSettings(response);
            setCashflowStartDay(response.cashflow_period_start_day);
            setLastLoadedRefreshKey(refreshKey);
            onCashflowPeriodChanged(response.cashflow_period_start_day);
            setMessage("Pengaturan periode cashflow berhasil disimpan.");
        } catch (requestError) {
            if (axios.isAxiosError(requestError) && requestError.response?.status === 401) {
                onUnauthorized("Sesi kamu sudah berakhir. Silakan buka ulang Mini App.");
                return;
            }
            setError(errorMessage(requestError));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <section className="transactions-section" aria-labelledby="settings-title">
            <div className="section-header">
                <div>
                    <h2 id="settings-title">Periode cashflow</h2>
                    <p className="section-description">
                        Samakan Dashboard, Budget, dan AI Advisor dengan siklus gajian kamu.
                    </p>
                </div>
            </div>

            {isLoading && settings === null ? (
                <div className="list-state" aria-busy="true">
                    Memuat pengaturan...
                </div>
            ) : (
                <form className="transaction-form" onSubmit={handleSubmit}>
                    <div className="form-grid">
                        <label>
                            Tanggal mulai periode cashflow
                            <input
                                required
                                min="1"
                                max="31"
                                type="number"
                                inputMode="numeric"
                                value={cashflowStartDay}
                                onChange={(event) =>
                                    setCashflowStartDay(Number(event.target.value))
                                }
                            />
                        </label>
                    </div>
                    <p className="muted-text settings-help">
                        Pilih tanggal mulai periode cashflow kamu. Contoh: pilih 29 jika
                        gajian biasanya tanggal 29. Dashboard, Budget, dan AI Advisor akan
                        dihitung dari tanggal tersebut sampai sehari sebelum periode berikutnya.
                    </p>
                    <div className="form-actions">
                        <button className="primary-button" disabled={isSaving} type="submit">
                            {isSaving ? "Menyimpan..." : "Simpan pengaturan"}
                        </button>
                    </div>
                </form>
            )}

            {message ? (
                <p className="list-state success-state" role="status">
                    {message}
                </p>
            ) : null}
            {error ? (
                <p className="inline-error" role="alert">
                    {error}
                </p>
            ) : null}
        </section>
    );
}
