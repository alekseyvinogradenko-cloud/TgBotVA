"use client";
import { useEffect, useState } from "react";
import { getTelegram } from "@/lib/telegram";
import { useTgBackButton } from "@/lib/useTgBackButton";
import {
  useSettings,
  useUpdateSettings,
  AI_MODELS,
  TIMEZONES,
} from "@/lib/useSettings";

export function SettingsSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const settings = useSettings(open);
  const update = useUpdateSettings();
  const [timeDraft, setTimeDraft] = useState("");

  useTgBackButton(open, onClose);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [open]);

  useEffect(() => {
    if (settings.data) setTimeDraft(settings.data.notify_morning_time);
  }, [settings.data]);

  if (!open) return null;

  const s = settings.data;
  const haptic = () => getTelegram()?.HapticFeedback?.impactOccurred("light");

  return (
    <>
      <div onClick={onClose} style={backdrop} />
      <div style={sheet}>
        <div style={{ display: "flex", justifyContent: "center", padding: "8px 0 4px" }}>
          <span style={{ width: 38, height: 4, borderRadius: 2, background: "#3a3b42" }} />
        </div>
        <div style={headerRow}>
          <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0, color: "#fff" }}>Настройки</h2>
          <button onClick={onClose} style={closeBtn} aria-label="Закрыть">×</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 24px" }}>
          {settings.isLoading || !s ? (
            <div style={{ color: "#8b8d94", fontSize: 13, padding: 12 }}>Загружаю…</div>
          ) : (
            <>
              {/* Notifications */}
              <label style={label}>Уведомления</label>
              <Toggle
                text="☀️ Утренний дайджест"
                on={s.notify_morning_digest}
                onClick={() => {
                  haptic();
                  update.mutate({ notify_morning_digest: !s.notify_morning_digest });
                }}
              />
              {s.notify_morning_digest && (
                <div style={{ display: "flex", gap: 6, margin: "6px 0 2px", alignItems: "center" }}>
                  <span style={{ fontSize: 13, color: "#8b8d94" }}>Время:</span>
                  <input
                    value={timeDraft}
                    onChange={(e) => setTimeDraft(e.target.value)}
                    onBlur={() => {
                      if (timeDraft !== s.notify_morning_time)
                        update.mutate({ notify_morning_time: timeDraft });
                    }}
                    placeholder="09:00"
                    style={{ ...input, width: 80 }}
                  />
                </div>
              )}
              <Toggle
                text="📊 Еженедельный отчёт"
                on={s.notify_weekly_report}
                onClick={() => {
                  haptic();
                  update.mutate({ notify_weekly_report: !s.notify_weekly_report });
                }}
              />

              {/* AI model */}
              <div style={{ height: 16 }} />
              <label style={label}>AI-модель для распознавания задач</label>
              {AI_MODELS.map((m) => (
                <Radio
                  key={m.value}
                  text={m.label}
                  selected={s.ai_model === m.value}
                  onClick={() => {
                    haptic();
                    update.mutate({ ai_model: m.value });
                  }}
                />
              ))}

              {/* Timezone */}
              <div style={{ height: 16 }} />
              <label style={label}>Часовой пояс</label>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {TIMEZONES.map((tz) => (
                  <button
                    key={tz}
                    onClick={() => {
                      haptic();
                      update.mutate({ timezone: tz });
                    }}
                    style={{
                      ...chip,
                      background: s.timezone === tz ? "#6ab2f2" : "#2a2c33",
                      color: s.timezone === tz ? "#fff" : "#c0c2c7",
                      fontWeight: s.timezone === tz ? 600 : 400,
                    }}
                  >
                    {tz.split("/")[1]?.replace("_", " ") || tz}
                  </button>
                ))}
              </div>

              {update.isError && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#ff7878" }}>
                  Не удалось сохранить. Проверь формат и попробуй снова.
                </div>
              )}
              {update.isSuccess && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#22c55e" }}>
                  ✓ Сохранено
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

function Toggle({ text, on, onClick }: { text: string; on: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={row}>
      <span style={{ flex: 1, textAlign: "left", fontSize: 14, color: "#fff" }}>{text}</span>
      <span
        style={{
          width: 40,
          height: 24,
          borderRadius: 12,
          background: on ? "#22c55e" : "#3a3b42",
          position: "relative",
          transition: "background .15s",
          flexShrink: 0,
        }}
      >
        <span
          style={{
            position: "absolute",
            top: 2,
            left: on ? 18 : 2,
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: "#fff",
            transition: "left .15s",
          }}
        />
      </span>
    </button>
  );
}

function Radio({ text, selected, onClick }: { text: string; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={row}>
      <span style={{ flex: 1, textAlign: "left", fontSize: 13, color: "#fff" }}>{text}</span>
      <span
        style={{
          width: 18,
          height: 18,
          borderRadius: "50%",
          border: selected ? "5px solid #6ab2f2" : "2px solid #4e525c",
          flexShrink: 0,
        }}
      />
    </button>
  );
}

const backdrop: React.CSSProperties = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 50 };
const sheet: React.CSSProperties = {
  position: "fixed", left: 0, right: 0, bottom: 0, maxHeight: "85vh",
  background: "#1c1d22", borderTopLeftRadius: 18, borderTopRightRadius: 18,
  zIndex: 51, display: "flex", flexDirection: "column",
  paddingBottom: "env(safe-area-inset-bottom, 0px)",
};
const headerRow: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "space-between", padding: "4px 16px 12px",
};
const closeBtn: React.CSSProperties = {
  background: "transparent", border: "none", color: "#8b8d94", fontSize: 22, cursor: "pointer", padding: 4, lineHeight: 1,
};
const label: React.CSSProperties = {
  display: "block", fontSize: 11, color: "#8b8d94", textTransform: "uppercase",
  letterSpacing: "0.04em", fontWeight: 600, marginBottom: 8, marginTop: 4,
};
const row: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 10, width: "100%",
  padding: "11px 12px", background: "#22232a", border: "none",
  borderRadius: 10, marginBottom: 6, cursor: "pointer",
};
const chip: React.CSSProperties = {
  padding: "7px 12px", fontSize: 12, borderRadius: 14, border: "none", cursor: "pointer",
};
const input: React.CSSProperties = {
  padding: "8px 10px", background: "#22232a", border: "1px solid #2f3038",
  borderRadius: 8, color: "#fff", fontSize: 14, outline: "none",
};
