"use client";
import { useEffect, useState } from "react";
import { getTelegram } from "@/lib/telegram";
import {
  useMyProjects,
  useCreateProject,
  useArchiveProject,
} from "@/lib/useTmaProjects";

const COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444",
  "#06b6d4", "#a78bfa", "#fb923c", "#ec4899",
];

export function ProjectsSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const projects = useMyProjects(open, true); // include archived
  const createProject = useCreateProject();
  const archiveProject = useArchiveProject();

  const [name, setName] = useState("");
  const [color, setColor] = useState(COLORS[0]);

  useEffect(() => {
    if (!open) {
      setName("");
      setColor(COLORS[0]);
      createProject.reset();
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [open]);

  if (!open) return null;

  const active = (projects.data ?? []).filter((p) => !p.is_archived);
  const archived = (projects.data ?? []).filter((p) => p.is_archived);

  const handleCreate = async () => {
    if (name.trim().length < 2) return;
    getTelegram()?.HapticFeedback?.notificationOccurred("success");
    await createProject.mutateAsync({ name: name.trim(), color });
    setName("");
  };

  return (
    <>
      <div onClick={onClose} style={backdropStyle} />
      <div style={sheetStyle}>
        <div style={{ display: "flex", justifyContent: "center", padding: "8px 0 4px" }}>
          <span style={{ width: 38, height: 4, borderRadius: 2, background: "#3a3b42" }} />
        </div>
        <div style={headerRow}>
          <h2 style={{ fontSize: 17, fontWeight: 600, margin: 0, color: "#fff" }}>Проекты</h2>
          <button onClick={onClose} style={closeBtn} aria-label="Закрыть">×</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "0 16px 16px" }}>
          {/* Create */}
          <label style={labelStyle}>Новый проект</label>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              placeholder="Название проекта"
              style={inputStyle}
            />
            <button
              onClick={handleCreate}
              disabled={name.trim().length < 2 || createProject.isPending}
              style={{
                ...addBtn,
                opacity: name.trim().length < 2 || createProject.isPending ? 0.5 : 1,
              }}
            >
              +
            </button>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            {COLORS.map((c) => (
              <button
                key={c}
                onClick={() => setColor(c)}
                style={{
                  width: 26,
                  height: 26,
                  borderRadius: "50%",
                  background: c,
                  border: color === c ? "2px solid #fff" : "2px solid transparent",
                  cursor: "pointer",
                }}
                aria-label={c}
              />
            ))}
          </div>

          {/* Active projects */}
          <div style={{ height: 20 }} />
          <label style={labelStyle}>
            Активные{active.length ? ` (${active.length})` : ""}
          </label>
          {projects.isLoading && (
            <div style={{ fontSize: 12, color: "#8b8d94" }}>Загружаю…</div>
          )}
          {active.map((p) => (
            <ProjectRow
              key={p.id}
              name={p.name}
              color={p.color}
              actionLabel="В архив"
              onAction={() => {
                getTelegram()?.HapticFeedback?.impactOccurred("light");
                archiveProject.mutate({ id: p.id, archived: true });
              }}
            />
          ))}
          {!projects.isLoading && active.length === 0 && (
            <div style={{ fontSize: 12, color: "#8b8d94" }}>Пока нет проектов. Создай первый выше.</div>
          )}

          {/* Archived */}
          {archived.length > 0 && (
            <>
              <div style={{ height: 16 }} />
              <label style={labelStyle}>Архив ({archived.length})</label>
              {archived.map((p) => (
                <ProjectRow
                  key={p.id}
                  name={p.name}
                  color={p.color}
                  dimmed
                  actionLabel="Вернуть"
                  onAction={() => {
                    getTelegram()?.HapticFeedback?.impactOccurred("light");
                    archiveProject.mutate({ id: p.id, archived: false });
                  }}
                />
              ))}
            </>
          )}
        </div>
      </div>
    </>
  );
}

function ProjectRow({
  name,
  color,
  actionLabel,
  onAction,
  dimmed,
}: {
  name: string;
  color: string;
  actionLabel: string;
  onAction: () => void;
  dimmed?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 12px",
        background: "#22232a",
        borderRadius: 10,
        marginBottom: 6,
        opacity: dimmed ? 0.55 : 1,
      }}
    >
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color }} />
      <span style={{ flex: 1, fontSize: 14, color: "#fff" }}>{name}</span>
      <button onClick={onAction} style={rowAction}>{actionLabel}</button>
    </div>
  );
}

const backdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.55)",
  zIndex: 50,
};
const sheetStyle: React.CSSProperties = {
  position: "fixed",
  left: 0,
  right: 0,
  bottom: 0,
  maxHeight: "85vh",
  background: "#1c1d22",
  borderTopLeftRadius: 18,
  borderTopRightRadius: 18,
  zIndex: 51,
  display: "flex",
  flexDirection: "column",
  paddingBottom: "env(safe-area-inset-bottom, 0px)",
};
const headerRow: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "4px 16px 12px",
};
const closeBtn: React.CSSProperties = {
  background: "transparent",
  border: "none",
  color: "#8b8d94",
  fontSize: 22,
  cursor: "pointer",
  padding: 4,
  lineHeight: 1,
};
const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  color: "#8b8d94",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  fontWeight: 600,
  marginBottom: 6,
};
const inputStyle: React.CSSProperties = {
  flex: 1,
  padding: "10px 12px",
  background: "#22232a",
  border: "1px solid #2f3038",
  borderRadius: 10,
  color: "#fff",
  fontSize: 14,
  outline: "none",
};
const addBtn: React.CSSProperties = {
  padding: "0 16px",
  background: "#6ab2f2",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: 20,
  cursor: "pointer",
};
const rowAction: React.CSSProperties = {
  background: "transparent",
  border: "none",
  color: "#6ab2f2",
  fontSize: 12,
  cursor: "pointer",
  padding: "4px 6px",
};
