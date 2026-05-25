interface TelegramThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

interface TelegramHapticFeedback {
  impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: {
    user?: {
      id: number;
      first_name?: string;
      last_name?: string;
      username?: string;
    };
  };
  colorScheme: "light" | "dark";
  themeParams: TelegramThemeParams;
  HapticFeedback?: TelegramHapticFeedback;
  ready: () => void;
  expand: () => void;
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null;
}

export function initializeTelegramApp(): TelegramWebApp | null {
  const webApp = getTelegramWebApp();
  applyTelegramTheme(webApp);

  if (webApp) {
    webApp.ready();
    webApp.expand();
  }

  return webApp;
}

export function applyTelegramTheme(webApp: TelegramWebApp | null): void {
  const root = document.documentElement;
  const theme = webApp?.themeParams ?? {};

  root.style.setProperty("--app-bg", theme.bg_color ?? "#f5f7f6");
  root.style.setProperty("--app-panel", theme.secondary_bg_color ?? "#ffffff");
  root.style.setProperty("--app-text", theme.text_color ?? "#17211f");
  root.style.setProperty("--app-muted", theme.hint_color ?? "#65736f");
  root.style.setProperty("--app-accent", theme.button_color ?? "#0f9f8a");
  root.style.setProperty("--app-accent-strong", theme.link_color ?? "#087b6c");
  root.style.setProperty("--app-button-text", theme.button_text_color ?? "#ffffff");
  root.style.setProperty("--app-border", webApp?.colorScheme === "dark" ? "#31403d" : "#dce6e2");

  if (webApp?.colorScheme === "dark") {
    root.style.setProperty("--app-bg", theme.bg_color ?? "#101715");
    root.style.setProperty("--app-panel", theme.secondary_bg_color ?? "#18211f");
  }
}

export function hapticTap(): void {
  getTelegramWebApp()?.HapticFeedback?.impactOccurred("light");
}

export function openExternalLink(url: string): void {
  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.openLink(url);
    return;
  }

  window.open(url, "_blank", "noopener,noreferrer");
}

export function getTelegramInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}

export function getTelegramUserName(): string {
  const user = getTelegramWebApp()?.initDataUnsafe?.user;
  if (!user) {
    return "Гость";
  }
  return user.first_name || user.username || "Пользователь";
}
