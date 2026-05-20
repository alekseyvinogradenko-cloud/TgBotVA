"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  applyTelegramTheme,
  getTelegram,
  type TelegramUser,
} from "@/lib/telegram";
import { authenticate, type AuthResponse } from "@/lib/tmaAuth";

type Status = "loading" | "ready" | "error";

export default function MiniAppPage() {
  return (
    <Suspense fallback={null}>
      <MiniAppInner />
    </Suspense>
  );
}

function MiniAppInner() {
  const params = useSearchParams();
  const workspaceId = params.get("ws");

  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [tgUser, setTgUser] = useState<TelegramUser | null>(null);
  const [auth, setAuth] = useState<AuthResponse | null>(null);

  useEffect(() => {
    const tg = getTelegram();
    if (!tg) {
      setStatus("error");
      setError("Это окно нужно открывать из Telegram (кнопка «📱 Открыть приложение» в боте).");
      return;
    }

    tg.ready();
    tg.expand();
    applyTelegramTheme(tg);
    setTgUser(tg.initDataUnsafe.user ?? null);

    if (!workspaceId) {
      setStatus("error");
      setError("В URL не указан workspace (?ws=...). Открой приложение из бота заново.");
      return;
    }
    if (!tg.initData) {
      setStatus("error");
      setError("Telegram не передал initData. Перезапусти приложение из бота.");
      return;
    }

    authenticate(tg.initData, workspaceId)
      .then((r) => {
        setAuth(r);
        setStatus("ready");
      })
      .catch((e) => {
        setStatus("error");
        const msg =
          e?.response?.data?.detail ||
          e?.message ||
          "Не удалось авторизоваться";
        setError(typeof msg === "string" ? msg : JSON.stringify(msg));
      });
  }, [workspaceId]);

  return (
    <main style={{ padding: "24px 18px", maxWidth: 520, margin: "0 auto" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>
        {status === "ready" && auth
          ? `Привет, ${auth.user.first_name} 👋`
          : "SpetAssist"}
      </h1>
      <p style={{ color: "var(--tg-hint, #8b8d94)", fontSize: 13, marginTop: 6 }}>
        Stage 1 · скелет Mini App
      </p>

      <section
        style={{
          marginTop: 22,
          padding: 16,
          background: "var(--tg-secondary-bg, #22232a)",
          borderRadius: 14,
          fontSize: 13,
          lineHeight: 1.55,
        }}
      >
        {status === "loading" && <div>⏳ Авторизация в Telegram…</div>}

        {status === "ready" && auth && (
          <>
            <div>
              ✅ Авторизован как <b>{auth.user.first_name}</b>
              {auth.user.telegram_username && (
                <span style={{ color: "var(--tg-hint, #8b8d94)" }}>
                  {" "}
                  · @{auth.user.telegram_username}
                </span>
              )}
            </div>
            <div style={{ marginTop: 8 }}>
              🏢 Workspace: <b>{auth.workspace.name}</b>
            </div>
            <div
              style={{
                marginTop: 12,
                paddingTop: 12,
                borderTop: "1px solid rgba(255,255,255,0.08)",
                color: "var(--tg-hint, #8b8d94)",
                fontSize: 11,
              }}
            >
              JWT (debug): <code>{auth.access_token.slice(0, 24)}…</code>
              <br />
              Telegram ID: {tgUser?.id ?? "—"}
            </div>
          </>
        )}

        {status === "error" && (
          <div style={{ color: "#ff7878" }}>
            ⚠️ {error}
          </div>
        )}
      </section>

      <p
        style={{
          marginTop: 22,
          color: "var(--tg-hint, #8b8d94)",
          fontSize: 12,
          lineHeight: 1.5,
        }}
      >
        Дальше: на этом фундаменте — список задач (B-v2 дизайн), создание, детали, назначение исполнителя.
      </p>
    </main>
  );
}
