interface ImportMetaEnv {
    readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}

interface Window {
    Telegram?: {
        Login?: {
            auth?: (options: Record<string, unknown>) => void;
        };
        WebApp?: {
            initData?: string;
            initDataUnsafe?: Record<string, unknown>;
        };
    };
}
