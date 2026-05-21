"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  applyTelegramTheme,
  getTelegram,
  type TelegramUser,
} from "@/lib/telegram";
import { authenticate, type AuthResponse } from "@/lib/tmaAuth";
import { useMyTasks, type TmaTask } from "@/lib/useTmaTasks";
import { useTgMainButton } from "@/lib/useTgMainButton";
import { useSetStatus } from "@/lib/useTaskDetail";
import { CreateTaskSheet } from "./_components/CreateTaskSheet";
import { TaskDetailScreen } from "./_components/TaskDetailScreen";
import { ProjectsSheet } from "./_components/ProjectsSheet";

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
      setError("Открой это из Telegram-бота (кнопка «📱 Открыть приложение»).");
      return;
    }
    tg.ready();
    tg.expand();
    applyTelegramTheme(tg);
    setTgUser(tg.initDataUnsafe.user ?? null);

    if (!workspaceId) {
      setStatus("error");
      setError("В URL не указан workspace. Открой приложение из бота заново.");
      return;
    }
    if (!tg.initData) {
      setStatus("error");
      setError("Telegram не передал initData. Перезапусти приложение.");
      return;
    }

    authenticate(tg.initData, workspaceId)
      .then((r) => {
        setAuth(r);
        setStatus("ready");
      })
      .catch((e) => {
        setStatus("error");
        const msg = e?.response?.data?.detail || e?.message || "Не удалось авторизоваться";
        setError(typeof msg === "string" ? msg : JSON.stringify(msg));
      });
  }, [workspaceId]);

  const tasksQuery = useMyTasks(status === "ready");

  if (status === "loading") return <CenterStatus text="⏳ Авторизация в Telegram…" />;
  if (status === "error")
    return <CenterStatus text={`⚠️ ${error}`} tone="error" />;

  return (
    <TaskBoard
      userName={auth?.user.first_name ?? "—"}
      workspaceName={auth?.workspace.name ?? ""}
      tasks={tasksQuery.data ?? []}
      loading={tasksQuery.isLoading}
      refetch={() => tasksQuery.refetch()}
    />
  );
}

// ─── Status screen ────────────────────────────────────────────────────────────

function CenterStatus({ text, tone }: { text: string; tone?: "error" }) {
  return (
    <main
      style={{
        minHeight: "70vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 18px",
      }}
    >
      <div
        style={{
          fontSize: 14,
          color: tone === "error" ? "#ff7878" : "#8b8d94",
          textAlign: "center",
          maxWidth: 320,
          lineHeight: 1.5,
        }}
      >
        {text}
      </div>
    </main>
  );
}

// ─── Main board ───────────────────────────────────────────────────────────────

function TaskBoard({
  userName,
  workspaceName,
  tasks,
  loading,
  refetch,
}: {
  userName: string;
  workspaceName: string;
  tasks: TmaTask[];
  loading: boolean;
  refetch: () => void;
}) {
  // Pick featured task: first overdue, else first urgent-priority
  const featured = useMemo(() => {
    const overdue = tasks.find((t) => t.is_overdue);
    if (overdue) return overdue;
    return tasks.find((t) => t.priority === "urgent" && t.status !== "done") ?? null;
  }, [tasks]);

  const [activeProject, setActiveProject] = useState<string | null>(null);

  const projects = useMemo(() => {
    const map = new Map<string, { id: string; name: string; color: string }>();
    for (const t of tasks) {
      if (!map.has(t.project.id)) map.set(t.project.id, t.project);
    }
    return Array.from(map.values());
  }, [tasks]);

  const filteredTasks = useMemo(() => {
    if (!activeProject) return tasks;
    return tasks.filter((t) => t.project.id === activeProject);
  }, [tasks, activeProject]);

  const todayCount = useMemo(() => {
    const todayEnd = new Date();
    todayEnd.setHours(23, 59, 59, 999);
    return tasks.filter((t) => t.due_date && new Date(t.due_date) <= todayEnd).length;
  }, [tasks]);
  const overdueCount = tasks.filter((t) => t.is_overdue).length;

  // Sheet for new-task flow + detail screen navigation
  const [sheetOpen, setSheetOpen] = useState(false);
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  // TG MainButton — opens create-task flow. Hidden while any sheet/detail is open.
  useTgMainButton({
    text: "+ Новая задача",
    visible: !sheetOpen && !selectedTaskId && !projectsOpen,
    onClick: () => {
      const tg = getTelegram();
      tg?.HapticFeedback?.impactOccurred("light");
      setSheetOpen(true);
    },
    color: "#6ab2f2",
    textColor: "#ffffff",
  });

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        background: "#17181c",
        color: "#ffffff",
      }}
    >
      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", paddingBottom: 64 }}>
        {/* Greeting */}
        <header
          style={{
            padding: "18px 18px 14px",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div style={{ minWidth: 0 }}>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "-0.01em",
              margin: 0,
            }}
          >
            Привет, {userName} 👋
          </h1>
          <div
            style={{
              fontSize: 13,
              color: "#8b8d94",
              marginTop: 2,
            }}
          >
            {todayCount} на сегодня
            {overdueCount > 0 && (
              <>
                {" · "}
                <span style={{ color: "#ff5757" }}>{overdueCount} горит</span>
              </>
            )}
            {workspaceName && (
              <span style={{ color: "#8b8d94" }}>
                {" · "}
                {workspaceName}
              </span>
            )}
          </div>
          </div>
          <button
            onClick={() => {
              getTelegram()?.HapticFeedback?.impactOccurred("light");
              setProjectsOpen(true);
            }}
            style={{
              flexShrink: 0,
              width: 38,
              height: 38,
              borderRadius: 10,
              background: "#22232a",
              border: "none",
              color: "#fff",
              fontSize: 18,
              cursor: "pointer",
            }}
            aria-label="Проекты"
          >
            📁
          </button>
        </header>

        {loading && (
          <div style={{ padding: "16px 18px", color: "#8b8d94", fontSize: 13 }}>
            Загружаю задачи…
          </div>
        )}

        {!loading && tasks.length === 0 && (
          <div
            style={{
              margin: "14px 14px",
              padding: 16,
              background: "#22232a",
              borderRadius: 14,
              fontSize: 13,
              lineHeight: 1.6,
              color: "#8b8d94",
            }}
          >
            <div style={{ color: "#ffffff", fontWeight: 600, marginBottom: 4 }}>
              Пусто 🎉
            </div>
            Активных задач нет. Жми «+ Новая задача» внизу, чтобы добавить.
          </div>
        )}

        {/* Featured urgent card */}
        {featured && <UrgentCard task={featured} onOpen={setSelectedTaskId} />}

        {/* Regular task cards (excluding featured) */}
        <div style={{ padding: "0 14px" }}>
          {filteredTasks
            .filter((t) => t.id !== featured?.id)
            .map((t) => (
              <TaskCard key={t.id} task={t} onOpen={setSelectedTaskId} />
            ))}
        </div>
      </div>

      {/* Task detail screen (overlay) */}
      {selectedTaskId && (
        <TaskDetailScreen taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
      )}

      <CreateTaskSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onCreated={refetch}
      />

      <ProjectsSheet open={projectsOpen} onClose={() => setProjectsOpen(false)} />

      {/* Sticky project filter chips */}
      {projects.length > 0 && (
        <div
          style={{
            position: "sticky",
            bottom: 0,
            background: "rgba(23,24,28,0.92)",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
            borderTop: "0.5px solid rgba(255,255,255,0.08)",
            padding: "8px 14px",
            display: "flex",
            gap: 6,
            overflowX: "auto",
          }}
        >
          <Chip
            active={activeProject === null}
            label={`Все · ${tasks.length}`}
            onClick={() => setActiveProject(null)}
          />
          {projects.map((p) => (
            <Chip
              key={p.id}
              active={activeProject === p.id}
              label={p.name}
              dot={p.color}
              onClick={() => setActiveProject(p.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Components ───────────────────────────────────────────────────────────────

function UrgentCard({ task, onOpen }: { task: TmaTask; onOpen: (id: string) => void }) {
  const formatted = formatDueRelative(task.due_date);
  const isOverdue = task.is_overdue;
  const setStatus = useSetStatus(task.id);

  return (
    <div
      onClick={() => onOpen(task.id)}
      style={{
        margin: "0 14px 10px",
        padding: 14,
        cursor: "pointer",
        background: isOverdue
          ? "linear-gradient(135deg,#3d1417,#5c1d22)"
          : "linear-gradient(135deg,#3d2814,#5c3d1d)",
        borderRadius: 16,
        border: isOverdue ? "1px solid #6e2226" : "1px solid #6e4a22",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <span
          style={{
            fontSize: 10,
            padding: "2px 7px",
            background: isOverdue ? "rgba(255,87,87,0.25)" : "rgba(255,178,87,0.25)",
            color: isOverdue ? "#ff7878" : "#ffb878",
            borderRadius: 5,
            fontWeight: 700,
            letterSpacing: "0.04em",
          }}
        >
          {isOverdue ? "⚠ ПРОСРОЧЕНО" : "🔥 СРОЧНО"}
        </span>
      </div>
      <div style={{ fontSize: 15, color: "#fff", fontWeight: 600, lineHeight: 1.3 }}>
        {task.title}
      </div>
      {formatted && (
        <div style={{ fontSize: 11, color: isOverdue ? "#ff9595" : "#ffc795", marginTop: 6 }}>
          ⏱ {formatted}
        </div>
      )}
      <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
        <button
          style={btnStyle("rgba(255,255,255,0.12)", "#fff", 600)}
          onClick={(e) => {
            e.stopPropagation();
            getTelegram()?.HapticFeedback?.notificationOccurred("success");
            setStatus.mutate("done");
          }}
        >
          {setStatus.isPending ? "…" : "✓ Готово"}
        </button>
        <button
          style={btnStyle("rgba(255,255,255,0.06)", "#fff", 400)}
          onClick={(e) => {
            e.stopPropagation();
            getTelegram()?.HapticFeedback?.impactOccurred("light");
            onOpen(task.id);
          }}
        >
          Перенести
        </button>
      </div>
    </div>
  );
}

function TaskCard({ task, onOpen }: { task: TmaTask; onOpen: (id: string) => void }) {
  const inProgress = task.status === "in_progress";
  const projectColor = task.project.color || "#6e6e76";

  return (
    <div
      onClick={() => onOpen(task.id)}
      style={{
        margin: "0 0 8px",
        padding: "13px 14px",
        background: "#22232a",
        borderRadius: 14,
        cursor: "pointer",
        borderLeft: inProgress ? "3px solid #6ab2f2" : "3px solid transparent",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div
          style={{
            width: 18,
            height: 18,
            border: inProgress ? "1.5px solid #6ab2f2" : "1.5px solid #4e525c",
            borderRadius: "50%",
            flexShrink: 0,
            marginTop: 1,
            background: inProgress ? "#6ab2f2" : "transparent",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {inProgress && (
            <span
              style={{
                width: 5,
                height: 5,
                background: "#22232a",
                borderRadius: "50%",
              }}
            />
          )}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, color: "#ffffff", fontWeight: 500 }}>
            {task.title}
          </div>
          <div style={{ display: "flex", gap: 7, marginTop: 5, alignItems: "center", flexWrap: "wrap" }}>
            {task.due_date && (
              <span style={{ fontSize: 10, color: "#8b8d94" }}>
                🕐 {formatDueRelative(task.due_date)}
              </span>
            )}
            {task.due_date && (
              <span style={{ fontSize: 10, color: "#8b8d94" }}>·</span>
            )}
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
                fontSize: 10,
                color: "#8b8d94",
              }}
            >
              <span
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: projectColor,
                }}
              />
              {task.project.name}
            </span>
            {inProgress && (
              <span style={{ fontSize: 10, color: "#6ab2f2", fontWeight: 600 }}>В РАБОТЕ</span>
            )}
          </div>
        </div>
        {task.assignee && (
          <div
            title={task.assignee.first_name}
            style={{
              width: 22,
              height: 22,
              borderRadius: "50%",
              background: avatarColor(task.assignee.id),
              color: "#fff",
              fontSize: 9,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            {task.assignee.initials}
          </div>
        )}
      </div>
    </div>
  );
}

function Chip({
  active,
  label,
  dot,
  onClick,
}: {
  active: boolean;
  label: string;
  dot?: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "7px 12px",
        fontSize: 11,
        borderRadius: 14,
        whiteSpace: "nowrap",
        flexShrink: 0,
        background: active ? "#6ab2f2" : "#2a2c33",
        color: active ? "#fff" : "#c0c2c7",
        fontWeight: active ? 600 : 400,
        border: "none",
        cursor: "pointer",
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
      }}
    >
      {dot && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: dot,
            display: "inline-block",
          }}
        />
      )}
      {label}
    </button>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function btnStyle(bg: string, color: string, weight: number): React.CSSProperties {
  return {
    flex: 1,
    padding: "8px 0",
    background: bg,
    borderRadius: 8,
    textAlign: "center",
    fontSize: 12,
    color,
    fontWeight: weight,
    border: "none",
    cursor: "pointer",
  };
}

const AVATAR_COLORS = ["#fb923c", "#06b6d4", "#a78bfa", "#f43f5e", "#22c55e", "#f59e0b"];
function avatarColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}

function formatDueRelative(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  if (diffDays < -1) return `просрочено ${Math.abs(diffDays)} дн.`;
  if (diffDays === -1) return `вчера, ${hh}:${mm}`;
  if (diffDays === 0) return `сегодня · ${hh}:${mm}`;
  if (diffDays === 1) return `завтра · ${hh}:${mm}`;
  if (diffDays < 7) return `через ${diffDays} дн.`;
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
}
