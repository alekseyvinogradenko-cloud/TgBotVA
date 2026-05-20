import type { Metadata } from "next";
import Script from "next/script";

export const metadata: Metadata = {
  title: "SpetAssist",
  description: "Telegram Mini App for personal task management",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* Official Telegram WebApp SDK — must load before our client code reads window.Telegram */}
      <Script
        src="https://telegram.org/js/telegram-web-app.js"
        strategy="beforeInteractive"
      />
      <div
        style={{
          minHeight: "100vh",
          background: "#17181c",
          color: "#ffffff",
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif",
        }}
      >
        {children}
      </div>
    </>
  );
}
