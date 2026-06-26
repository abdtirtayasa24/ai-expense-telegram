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
