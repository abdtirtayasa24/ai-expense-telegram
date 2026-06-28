export type PageMenuTarget = "budget" | "advisor" | "transactions";

interface PageMenuProps {
    onOpen: (page: PageMenuTarget) => void;
}

const menuItems: Array<{
    page: PageMenuTarget;
    title: string;
    description: string;
}> = [
    {
        page: "budget",
        title: "Budget",
        description: "Atur dan pantau batas pengeluaran bulanan per kategori.",
    },
    {
        page: "advisor",
        title: "AI Advisor",
        description: "Minta insight dan saran cashflow berdasarkan data transaksi kamu.",
    },
    {
        page: "transactions",
        title: "Transaksi",
        description: "Tambah, edit, atau hapus pemasukan dan pengeluaran manual.",
    },
];

export function PageMenu({ onOpen }: PageMenuProps) {
    return (
        <section className="page-menu" aria-labelledby="page-menu-title">
            <div className="section-header">
                <div>
                    <p className="eyebrow">Menu</p>
                    <h2 id="page-menu-title">Kelola keuangan kamu</h2>
                </div>
            </div>
            <div className="page-menu-grid">
                {menuItems.map((item) => (
                    <button
                        key={item.page}
                        className="page-menu-card"
                        type="button"
                        onClick={() => onOpen(item.page)}
                    >
                        <span>{item.title}</span>
                        <small>{item.description}</small>
                    </button>
                ))}
            </div>
        </section>
    );
}
