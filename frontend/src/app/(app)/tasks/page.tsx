"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi, projectsApi, type Task, type TaskStatus, type TaskPriority } from "@/lib/api";
import { useWorkspace } from "@/lib/useWorkspace";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { CheckCircle2, Circle, Clock, AlertCircle, Plus } from "lucide-react";
import { clsx } from "clsx";

const STATUS_OPTIONS: { value: TaskStatus | "all"; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "todo", label: "К выполнению" },
  { value: "in_progress", label: "В работе" },
  { value: "done", label: "Выполнено" },
];

const PRIORITY_ICONS: Record<TaskPriority, string> = {
  low: "🟢", medium: "🟡", high: "🟠", urgent: "🔴",
};

const STATUS_ICONS: Record<TaskStatus, string> = {
  todo: "⬜", in_progress: "🔄", done: "✅", cancelled: "❌",
};

export default function TasksPage() {
  const { workspaceId } = useWorkspace();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all");
  const [projectFilter, setProjectFilter] = useState<string>("all");

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks", workspaceId],
    queryFn: () => tasksApi.getWorkspaceTasks(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: projects = [] } = useQuery({
    queryKey: ["projects", workspaceId],
    queryFn: () => projectsApi.getWorkspaceProjects(workspaceId!),
    enabled: !!workspaceId,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Task> }) =>
      tasksApi.updateTask(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const filtered = tasks.filter((t) => {
    if (statusFilter !== "all" && t.status !== statusFilter) return false;
    if (projectFilter !== "all" && t.project_id !== projectFilter) return false;
    return true;
  });

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Выбери пространство в настройках
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Задачи</h1>
        <span className="text-sm text-gray-400">{filtered.length} задач</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s.value}
              onClick={() => setStatusFilter(s.value)}
              className={clsx(
                "px-3 py-1 rounded-md text-sm font-medium transition",
                statusFilter === s.value
                  ? "bg-white text-indigo-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              )}
            >
              {s.label}
            </button>
          ))}
        </div>

        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-700 bg-white"
        >
          <option value="all">Все проекты</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Tasks table */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Загрузка...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Нет задач</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 divide-y divide-gray-50">
          {filtered.map((task) => {
            const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== "done";
            const project = projects.find((p) => p.id === task.project_id);
            return (
              <div key={task.id} className="flex items-center gap-3 p-3 hover:bg-gray-50 transition">
                <button
                  onClick={() =>
                    updateMutation.mutate({
                      id: task.id,
                      data: { status: task.status === "done" ? "todo" : "done" },
                    })
                  }
                  className="shrink-0 text-gray-400 hover:text-green-500 transition"
                >
                  {task.status === "done" ? (
                    <CheckCircle2 size={18} className="text-green-500" />
                  ) : (
                    <Circle size={18} />
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  <span className={clsx("text-sm font-medium", task.status === "done" && "line-through text-gray-400")}>
                    {task.title}
                  </span>
                  {project && (
                    <span className="ml-2 text-xs text-gray-400">📁 {project.name}</span>
                  )}
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-sm">{PRIORITY_ICONS[task.priority]}</span>
                  {task.due_date && (
                    <span className={clsx("flex items-center gap-1 text-xs", isOverdue ? "text-red-500" : "text-gray-400")}>
                      {isOverdue ? <AlertCircle size={12} /> : <Clock size={12} />}
                      {format(new Date(task.due_date), "d MMM", { locale: ru })}
                    </span>
                  )}
                  <select
                    value={task.status}
                    onChange={(e) =>
                      updateMutation.mutate({ id: task.id, data: { status: e.target.value as TaskStatus } })
                    }
                    className="text-xs border border-gray-200 rounded px-1.5 py-0.5 text-gray-600"
                  >
                    <option value="todo">К выполнению</option>
                    <option value="in_progress">В работе</option>
                    <option value="done">Выполнено</option>
                    <option value="cancelled">Отменено</option>
                  </select>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
