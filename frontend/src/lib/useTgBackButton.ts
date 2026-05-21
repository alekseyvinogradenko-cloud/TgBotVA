"use client";
import { useEffect } from "react";
import { getTelegram } from "./telegram";

/**
 * Show the native Telegram BackButton while `active`, route its tap to `onBack`.
 * Hides on deactivate/unmount. Use in every modal/sheet/screen so the hardware
 * back gesture (Android) and TG back arrow close the overlay instead of the app.
 */
export function useTgBackButton(active: boolean, onBack: () => void) {
  useEffect(() => {
    const tg = getTelegram();
    if (!tg) return;
    const back = tg.BackButton;
    if (!active) {
      back.hide();
      return;
    }
    back.show();
    back.onClick(onBack);
    return () => {
      back.offClick(onBack);
      back.hide();
    };
  }, [active, onBack]);
}
