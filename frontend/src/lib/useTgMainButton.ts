"use client";
import { useEffect } from "react";
import { getTelegram } from "./telegram";

/**
 * Show/control Telegram's native MainButton (the persistent CTA at the bottom).
 * On unmount or when `visible=false`, the button is hidden.
 */
export function useTgMainButton(opts: {
  text: string;
  visible: boolean;
  onClick?: () => void;
  color?: string;
  textColor?: string;
}) {
  const { text, visible, onClick, color, textColor } = opts;

  useEffect(() => {
    const tg = getTelegram();
    if (!tg) return;
    const mb = tg.MainButton;

    if (!visible) {
      mb.hide();
      return;
    }
    mb.setText(text);
    if (color) {
      // setParams isn't typed in our wrapper but it's available at runtime in newer TG clients
      // Fallback to color property; both work depending on version.
      try {
        // @ts-expect-error optional runtime API
        mb.setParams?.({ color, text_color: textColor });
      } catch {}
    }
    mb.show();
    mb.enable();

    const handler = () => {
      onClick?.();
    };
    if (onClick) mb.onClick(handler);
    return () => {
      if (onClick) mb.offClick(handler);
      mb.hide();
    };
  }, [text, visible, onClick, color, textColor]);
}
