import { formatRupiah } from "./utils/currency";

export default function App() {
    return (
        <main className="app-shell">
            <section className="hero-card">
                <p className="eyebrow">Telegram Mini App</p>
                <h1>AI Expense Tracker</h1>
                <p className="description">
                    Placeholder dashboard untuk mencatat pengeluaran, melihat cashflow,
                    dan mendapatkan insight budgeting berbasis data transaksi.
                </p>
                <dl className="summary-grid" aria-label="Contoh ringkasan bulanan">
                    <div>
                        <dt>Pemasukan</dt>
                        <dd>{formatRupiah(0)}</dd>
                    </div>
                    <div>
                        <dt>Pengeluaran</dt>
                        <dd>{formatRupiah(0)}</dd>
                    </div>
                    <div>
                        <dt>Cashflow</dt>
                        <dd>{formatRupiah(0)}</dd>
                    </div>
                </dl>
                <p className="note">
                    Milestone berikutnya akan menghubungkan dashboard ini dengan autentikasi
                    Telegram Mini App dan API backend.
                </p>
            </section>
        </main>
    );
}
