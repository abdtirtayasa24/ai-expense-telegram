interface PageHeaderProps {
    titleId: string;
    title: string;
    description: string;
    onBack: () => void;
}

export function PageHeader({ titleId, title, description, onBack }: PageHeaderProps) {
    return (
        <section className="page-header" aria-labelledby={titleId}>
            <button className="secondary-button small" type="button" onClick={onBack}>
                ← Dashboard
            </button>
            <div>
                <h1 id={titleId}>{title}</h1>
                <p>{description}</p>
            </div>
        </section>
    );
}
