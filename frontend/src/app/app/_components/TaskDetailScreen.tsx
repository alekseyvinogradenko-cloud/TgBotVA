"use client";
import { useEffect, useState } from "react";
import { getTelegram } from "@/lib/telegram";
import {
  useTaskDetail,
  useSetStatus,
  useEditTask,
  useDeleteTask,
  useAddSubtask,
  useAddNote,
} from "@/lib/useTaskDetail";
import type { TaskPriority, TaskStatus } from "@/lib/useTmaTasks";

const STATUS_LABEL: Record<TaskStatus, { label: string; color: string; icon: string }> = {
  todo: { label: "К выполнению", color: "#8b8d94", icon: "⬜" },
  in_progress: { label: "В работе", color: "#6ab2f2", icon: "🔄" },
  done: { label: "Выполнено", color: "#22c55e", icon: "✅" },
  cancelled: { label: "Отменено", color: "#6e6e76", icon: "❌" },
};

const PRIORITY_LABEL: Record<TaskPriority, { label: string; dot: string }> = {
  low: { label: "Низкий", dot: "#22c55e" },
  medium: { label: "Средний", dot: "#f59e0b" },
  high: { label: "Высокий", dot: "#fb923c" },
  urgent: { label: "Срочный", dot: "#ef4444" },
};

export function TaskDetailScreen({
  taskId,
  onClose,
}: {
  taskId: string;
  onClose: () => void;
}) {
  const { data: task, isLoading } = useTaskDetail(taskId);
  const setStatus = useSetStatus(taskId);
  const editTask = useEditTask(taskId);
  const deleteTask = useDeleteTask(taskId);
  const addSubtask = useAddSubtask(taskId);
  const addNote = useAddNote(taskId);

  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [subtaskInput, setSubtaskInput] = useState("");
  const [noteInput, setNoteInput] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  // TG BackButton drives navigation back to the list
  useEffect(() => {
    const tg = getTelegram();
    if (!tg) return;
    const back = tg.BackButton;
    back.show();
    const handler = () => onClose();
    back.onClick(handler);
    return () => {
      back.offClick(handler);
      back.hide();
    };
  }, [onClose]);

  const haptic = (type: "light" | "medium" | "success") => {
    const tg = getTelegram();
    if (type === "success") tg?.HapticFeedback?.notificationOccurred("success");
    else tg?.HapticFeedback?.impactOccurred(type);
  };

  if (isLoading || !task) {
    return (
      <Screen>
        <div style={{ color: "#8b8d94", fontSize: 14, padding: 24 }}>Загружаю…</div>
      </Screen>
    );
  }

  const st = STATUS_LABEL[task.status];
  const pr = PRIORITY_LABEL[task.priority];
  const isDone = task.status === "done";

  return (
    <Screen>
      {/* Title (tap to edit) */}
      <div style={{ padding: "8px 18px 4px" }}>
        {editingTitle ? (
          <input
            autoFocus
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            onBlur={saveTitle}
            onKeyDown={(e) => e.key === "Enter" && saveTitle()}
            style={{
              width: "100%",
              fontSize: 20,
              fontWeight: 700,
              background: "#22232a",
              border: "1px solid #6ab2f2",
              borderRadius: 8,
              color: "#fff",
              padding: "6px 10px",
              outline: "none",
            }}
          />
        ) : (
          <h1
            onClick={() => {
              setTitleDraft(task.title);
              setEditingTitle(true);
            }}
            style={{
              fontSize: 20,
              fontWeight: 700,
              margin: 0,
              color: "#fff",
              lineHeight: 1.3,
              textDecoration: isDone ? "line-through" : "none",
              opacity: isDone ? 0.6 : 1,
            }}
          >
            {task.title}
            <span style={{ fontSize: 13, color: "#8b8d94", marginLeft: 8 }}>✏️</span>
          </h1>
        )}
      </div>

      {/* Meta chips */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: "8px 18px 16px" }}>
        <Meta icon={st.icon} text={st.label} color={st.color} />
        <Meta dot={pr.dot} text={pr.label} />
        <Meta dot={task.project.color} text={task.project.name} />
        {task.due_date && <Meta icon="🕐" text={formatDate(task.due_date)} color={task.is_overdue ? "#ff7878" : "#8b8d94"} />}
        {task.assignee && <Meta icon="👤" text={task.assignee.first_name} />}
      </div>

      {/* Status actions */}
      <div style={{ display: "flex", gap: 8, padding: "0 18px 16px" }}>
        {!isDone ? (
          <>
            <ActionBtn
              primary
              onClick={() => {
                haptic("success");
                setStatus.mutate("done");
              }}
            >
              ✓ Выполнено
            </ActionBtn>
            {task.status !== "in_progress" && (
              <ActionBtn
                onClick={() => {
                  haptic("light");
                  setStatus.mutate("in_progress");
                }}
              >
                🔄 В работу
              </ActionBtn>
            )}
          </>
        ) : (
          <ActionBtn
            onClick={() => {
              haptic("light");
              setStatus.mutate("todo");
            }}
          >
            ↩ Вернуть в работу
          </ActionBtn>
        )}
      </div>

      {/* Subtasks */}
      <Section title={`Подзадачи${task.subtasks.length ? ` (${task.subtasks.length})` : ""}`}>
        {task.subtasks.map((s) => (
          <div
            key={s.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 0",
              fontSize: 13,
              color: s.status === "done" ? "#8b8d94" : "#fff",
              textDecoration: s.status === "done" ? "line-through" : "none",
            }}
          >
            <span>{STATUS_LABEL[s.status].icon}</span>
            {s.title}
          </div>
        ))}
        <InlineAdd
          value={subtaskInput}
          onChange={setSubtaskInput}
          placeholder="Добавить подзадачу…"
          onSubmit={() => {
            if (!subtaskInput.trim()) return;
            haptic("light");
            addSubtask.mutate(subtaskInput.trim());
            setSubtaskInput("");
          }}
        />
      </Section>

      {/* Notes */}
      <Section title={`Заметки${task.notes.length ? ` (${task.notes.length})` : ""}`}>
        {task.notes.map((n) => (
          <div
            key={n.id}
            style={{
              padding: "8px 10px",
              background: "#22232a",
              borderRadius: 8,
              fontSize: 13,
              color: "#e7e7ea",
              marginBottom: 6,
            }}
          >
            {n.content}
            <div style={{ fontSize: 10, color: "#6e6e76", marginTop: 4 }}>
              {formatDate(n.created_at)}
            </div>
          </div>
        ))}
        <InlineAdd
          value={noteInput}
          onChange={setNoteInput}
          placeholder="Добавить заметку…"
          onSubmit={() => {
            if (!noteInput.trim()) return;
            haptic("light");
            addNote.mutate(noteInput.trim());
            setNoteInput("");
          }}
        />
      </Section>

      {/* Delete */}
      <div style={{ padding: "20px 18px 32px" }}>
        {!confirmDelete ? (
          <button onClick={() => setConfirmDelete(true)} style={deleteBtnStyle}>
            🗑️ Удалить задачу
          </button>
        ) : (
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setConfirmDelete(false)}
              style={{ ...deleteBtnStyle, background: "#2a2c33", color: "#fff", flex: 1 }}
            >
              Отмена
            </button>
            <button
              onClick={() => {
                haptic("medium");
                deleteTask.mutate(undefined, { onSuccess: onClose });
              }}
              style={{ ...deleteBtnStyle, background: "#ef4444", color: "#fff", flex: 1 }}
            >
              Точно удалить
            </button>
          </div>
        )}
      </div>
    </Screen>
  );

  function saveTitle() {
    setEditingTitle(false);
    const trimmed = titleDraft.trim();
    if (trimmed && trimmed !== task!.title) {
      editTask.mutate({ title: trimmed });
    }
  }
}

// ─── Layout helpers ───────────────────────────────────────────────────────────

function Screen({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#17181c",
        zIndex: 40,
        overflowY: "auto",
        animation: "tma-slide-in .2s ease",
      }}
    >
      {children}
      <style jsx>{`
        @keyframes tma-slide-in {
          from { transform: translateX(20px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: "0 18px 16px" }}>
      <div
        style={{
          fontSize: 11,
          color: "#8b8d94",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          fontWeight: 600,
          marginBottom: 8,
          paddingTop: 12,
          borderTop: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

function Meta({
  icon,
  dot,
  text,
  color,
}: {
  icon?: string;
  dot?: string;
  text: string;
  color?: string;
}) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "5px 10px",
        background: "#22232a",
        borderRadius: 10,
        fontSize: 12,
        color: color || "#c0c2c7",
      }}
    >
      {dot && (
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: dot, display: "inline-block" }} />
      )}
      {icon && <span>{icon}</span>}
      {text}
    </span>
  );
}

function ActionBtn({
  children,
  onClick,
  primary,
}: {
  children: React.ReactNode;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: "11px 0",
        background: primary ? "#22c55e" : "#2a2c33",
        color: "#fff",
        border: "none",
        borderRadius: 10,
        fontSize: 14,
        fontWeight: 600,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

function InlineAdd({
  value,
  onChange,
  placeholder,
  onSubmit,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  onSubmit: () => void;
}) {
  return (
    <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        placeholder={placeholder}
        style={{
          flex: 1,
          padding: "9px 12px",
          background: "#22232a",
          border: "1px solid #2f3038",
          borderRadius: 8,
          color: "#fff",
          fontSize: 13,
          outline: "none",
        }}
      />
      <button
        onClick={onSubmit}
        disabled={!value.trim()}
        style={{
          padding: "0 14px",
          background: value.trim() ? "#6ab2f2" : "#2a2c33",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          fontSize: 18,
          cursor: "pointer",
        }}
      >
        +
      </button>
    </div>
  );
}

const deleteBtnStyle: React.CSSProperties = {
  width: "100%",
  padding: "11px 0",
  background: "rgba(239,68,68,0.12)",
  color: "#ff7878",
  border: "none",
  borderRadius: 10,
  fontSize: 14,
  fontWeight: 500,
  cursor: "pointer",
};

function formatDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffDays = Math.round((date.getTime() - now.getTime()) / 86400000);
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  if (diffDays === 0) return `сегодня ${hh}:${mm}`;
  if (diffDays === 1) return `завтра ${hh}:${mm}`;
  if (diffDays === -1) return `вчера ${hh}:${mm}`;
  if (diffDays < -1) return `${Math.abs(diffDays)} дн. назад`;
  return `${date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })} ${hh}:${mm}`;
}
