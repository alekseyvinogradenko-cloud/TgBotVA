/**
 * Telegram Mini App SDK helpers.
 * Reads `window.Telegram.WebApp` injected by the official script
 * (loaded in src/app/app/layout.tsx).
 */

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
}

export interface TelegramThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: TelegramUser; auth_date?: number; hash?: string };
  themeParams: TelegramThemeParams;
  colorScheme: "light" | "dark";
  version: string;
  platform: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    setText: (text: string) => void;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  BackButton: {
    isVisible: boolean;
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  HapticFeedback: {
    impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
    notificationOccurred: (type: "error" | "success" | "warning") => void;
    selectionChanged: () => void;
  };
  onEvent: (event: string, cb: (...args: unknown[]) => void) => void;
  offEvent: (event: string, cb: (...args: unknown[]) => void) => void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export function getTelegram(): TelegramWebApp | null {
  if (typeof window === "undefined") return null;
  return window.Telegram?.WebApp ?? null;
}

/**
 * Apply Telegram theme params to CSS variables on documentElement.
 * Components can reference them via `var(--tg-bg)`, `var(--tg-text)`, etc.
 */
export function applyTelegramTheme(tg: TelegramWebApp) {
  const root = document.documentElement;
  const t = tg.themeParams;
  const map: Record<string, string | undefined> = {
    "--tg-bg": t.bg_color,
    "--tg-text": t.text_color,
    "--tg-hint": t.hint_color,
    "--tg-link": t.link_color,
    "--tg-btn": t.button_color,
    "--tg-btn-text": t.button_text_color,
    "--tg-secondary-bg": t.secondary_bg_color,
  };
  for (const [k, v] of Object.entries(map)) {
    if (v) root.style.setProperty(k, v);
  }
  root.dataset.tgColorScheme = tg.colorScheme;
}
