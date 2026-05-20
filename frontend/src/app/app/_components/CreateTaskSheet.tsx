"use client";
import { useEffect, useMemo, useState } from "react";
import { useMyProjects } from "@/lib/useTmaProjects";
import { useParseTask, useCreateTask } from "@/lib/useCreateTask";
import type { TaskPriority } from "@/lib/useTmaTasks";
import { getTelegram } from "@/lib/telegram";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
};

const PRIORITIES: { value: TaskPriority; label: string; dot: string }[] = [
  { value: "low", label: "Низкий", dot: "#22c55e" },
  { value: "medium", label: "Средний", dot: "#f59e0b" },
  { value: "high", label: "Высокий", dot: "#fb923c" },
  { value: "urgent", label: "Срочный", dot: "#ef4444" },
];

export function CreateTaskSheet({ open, onClose, onCreated }: Props) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState<string | null>(null);
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [parsedOnce, setParsedOnce] = useState(false);

  const projectsQuery = useMyProjects(open);
  const parseMutation = useParseTask();
  const createMutation = useCreateTask();

  // Auto-select first project once projects load
  useEffect(() => {
    if (open && projectsQuery.data && projectsQuery.data.length > 0 && !projectId) {
      setProjectId(projectsQuery.data[0].id);
    }
  }, [open, projectsQuery.data, projectId]);

  // Reset state when sheet closes
  useEffect(() => {
    if (!open) {
      setText("");
      setTitle("");
      setDueDate(null);
      setPriority("medium");
      setProjectId(null);
      setParsedOnce(false);
      parseMutation.reset();
      createMutation.reset();
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  // Lock body scroll while open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [open]);

  const handleParse = async () => {
    if (!text.trim()) return;
    getTelegram()?.HapticFeedback?.impactOccurred("light");
    try {
      const r = await parseMutation.mutateAsync(text.trim());
      setTitle(r.title);
      setDueDate(r.due_date);
      setPriority(r.priority);
      setParsedOnce(true);
    } catch {
      // mutation.error handles UI
    }
  };

  const canSave = useMemo(
    () => Boolean(title.trim() && projectId && !createMutation.isPending),
    [title, projectId, createMutation.isPending]
  );

  const handleSave = async () => {
    if (!canSave || !projectId) return;
    getTelegram()?.HapticFeedback?.notificationOccurred("success");
    try {
      await createMutation.mutateAsync({
        project_id: projectId,
        title: title.trim(),
        due_date: dueDate,
        priority,
      });
      onCreated();
      onClose();
    } catch {
      // mutation.error handles UI
    }
  };

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.55)",
          zIndex: 50,
          animation: "tma-fade .15s ease",
        }}
      />

      {/* Sheet */}
      <div
        style={{
          position: "fixed",
          left: 0,
          right: 0,
          bottom: 0,
          maxHeight: "90vh",
          background: "#1c1d22",
          borderTopLeftRadius: 18,
          borderTopRightRadius: 18,
          zIndex: 51,
          display: "flex",
          flexDirection: "column",
          animation: "tma-slide .22s cubic-bezier(.2,.8,.2,1)",
          paddingBottom: "env(safe-area-inset-bottom, 0px)",
        }}
      >
        {/* Drag handle */}
        <div style={{ display: "flex", justifyContent: "center", padding: "8px 0 4px" }}>
          <span
            style={{ width: 38, height: 4, borderRadius: 2, background: "#3a3b42" }}
          />
        </div>

        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "4px 16px 12px",
          }}
        >
          <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0, color: "#fff" }}>
            Новая задача
          </h2>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#8b8d94",
              fontSize: 22,
              cursor: "pointer",
              padding: 4,
              lineHeight: 1,
            }}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        {/* Body — scrollable */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 16px" }}>
          {/* Free-text input */}
          <label style={labelStyle}>Что нужно сделать?</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Купить молоко завтра в 18:00"
            rows={3}
            style={textareaStyle}
          />
          <button
            onClick={handleParse}
            disabled={!text.trim() || parseMutation.isPending}
            style={{
              ...secondaryBtnStyle,
              marginTop: 8,
              opacity: !text.trim() || parseMutation.isPending ? 0.5 : 1,
            }}
          >
            {parseMutation.isPending ? "🤖 Анализирую…" : "🤖 Распознать через AI"}
          </button>
          {parseMutation.isError && (
            <div style={{ marginTop: 8, fontSize: 12, color: "#ff7878" }}>
              Не удалось разобрать. Попробуй сформулировать иначе.
            </div>
          )}

          {/* Editable preview — visible after parse */}
          {parsedOnce && (
            <>
              <div style={{ height: 16 }} />
              <label style={labelStyle}>Название</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Название задачи"
                style={inputStyle}
              />

              <div style={{ height: 12 }} />
              <label style={labelStyle}>Когда</label>
              {dueDate ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    background: "#22232a",
                    border: "1px solid #2f3038",
                    borderRadius: 10,
                    padding: "10px 12px",
                    fontSize: 13,
                    color: "#fff",
                  }}
                >
                  🕐 {formatHumanDate(dueDate)}
                  <button
                    onClick={() => setDueDate(null)}
                    style={{
                      marginLeft: "auto",
                      background: "transparent",
                      border: "none",
                      color: "#8b8d94",
                      cursor: "pointer",
                      fontSize: 16,
                    }}
                    aria-label="Убрать дату"
                  >
                    ×
                  </button>
                </div>
              ) : (
                <div style={{ fontSize: 12, color: "#8b8d94" }}>
                  Без срока. AI не распознал дату — можно указать в тексте, например «завтра в 18:00».
                </div>
              )}

              <div style={{ height: 12 }} />
              <label style={labelStyle}>Приоритет</label>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {PRIORITIES.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setPriority(p.value)}
                    style={{
                      ...chipStyle,
                      background: priority === p.value ? "#6ab2f2" : "#2a2c33",
                      color: priority === p.value ? "#fff" : "#c0c2c7",
                      fontWeight: priority === p.value ? 600 : 400,
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: p.dot,
                        display: "inline-block",
                      }}
                    />
                    {p.label}
                  </button>
                ))}
              </div>

              <div style={{ height: 12 }} />
              <label style={labelStyle}>Проект</label>
              {projectsQuery.isLoading && (
                <div style={{ fontSize: 12, color: "#8b8d94" }}>Загружаю проекты…</div>
              )}
              {projectsQuery.data && projectsQuery.data.length === 0 && (
                <div style={{ fontSize: 12, color: "#ff7878" }}>
                  Нет проектов в этом workspace. Создай первый через бота: /projects
                </div>
              )}
              {projectsQuery.data && projectsQuery.data.length > 0 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {projectsQuery.data.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setProjectId(p.id)}
                      style={{
                        ...chipStyle,
                        background: projectId === p.id ? "#6ab2f2" : "#2a2c33",
                        color: projectId === p.id ? "#fff" : "#c0c2c7",
                        fontWeight: projectId === p.id ? 600 : 400,
                      }}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: p.color || "#6e6e76",
                          display: "inline-block",
                        }}
                      />
                      {p.name}
                    </button>
                  ))}
                </div>
              )}

              {createMutation.isError && (
                <div style={{ marginTop: 12, fontSize: 12, color: "#ff7878" }}>
                  Не удалось создать задачу. Попробуй ещё раз.
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {parsedOnce && (
          <div
            style={{
              display: "flex",
              gap: 8,
              padding: "10px 16px",
              borderTop: "1px solid rgba(255,255,255,0.06)",
              background: "#1c1d22",
            }}
          >
            <button onClick={onClose} style={cancelBtnStyle}>
              Отмена
            </button>
            <button
              onClick={handleSave}
              disabled={!canSave}
              style={{ ...primaryBtnStyle, opacity: canSave ? 1 : 0.5 }}
            >
              {createMutation.isPending ? "Сохраняю…" : "Сохранить"}
            </button>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes tma-fade {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes tma-slide {
          from { transform: translateY(100%); }
          to   { transform: translateY(0); }
        }
      `}</style>
    </>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  color: "#8b8d94",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  fontWeight: 600,
  marginBottom: 6,
};

const textareaStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  background: "#22232a",
  border: "1px solid #2f3038",
  borderRadius: 10,
  color: "#fff",
  fontSize: 14,
  fontFamily: "inherit",
  resize: "vertical",
  outline: "none",
};

const inputStyle: React.CSSProperties = {
  ...textareaStyle,
  resize: "none" as const,
};

const chipStyle: React.CSSProperties = {
  padding: "7px 12px",
  fontSize: 12,
  borderRadius: 14,
  border: "none",
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
};

const secondaryBtnStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 14px",
  background: "#2a2c33",
  border: "none",
  borderRadius: 10,
  color: "#fff",
  fontSize: 14,
  fontWeight: 500,
  cursor: "pointer",
};

const primaryBtnStyle: React.CSSProperties = {
  flex: 1,
  padding: "12px 14px",
  background: "#6ab2f2",
  border: "none",
  borderRadius: 10,
  color: "#fff",
  fontSize: 15,
  fontWeight: 600,
  cursor: "pointer",
};

const cancelBtnStyle: React.CSSProperties = {
  flex: 1,
  padding: "12px 14px",
  background: "#2a2c33",
  border: "none",
  borderRadius: 10,
  color: "#fff",
  fontSize: 15,
  fontWeight: 500,
  cursor: "pointer",
};

// ─── helpers ──────────────────────────────────────────────────────────────────

function formatHumanDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  const datePart = date.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
  let prefix = datePart;
  if (diffDays === 0) prefix = "сегодня";
  else if (diffDays === 1) prefix = "завтра";
  else if (diffDays === -1) prefix = "вчера";
  return `${prefix} · ${hh}:${mm}`;
}
