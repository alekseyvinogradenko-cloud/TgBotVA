"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi, tasksApi } from "@/lib/api";
import { useWorkspace } from "@/lib/useWorkspace";
import { FolderOpen, Plus, X } from "lucide-react";

export default function ProjectsPage() {
  const { workspaceId } = useWorkspace();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects", workspaceId],
    queryFn: () => projectsApi.getWorkspaceProjects(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: allTasks = [] } = useQuery({
    queryKey: ["tasks", workspaceId],
    queryFn: () => tasksApi.getWorkspaceTasks(workspaceId!),
    enabled: !!workspaceId,
  });

  const createMutation = useMutation({
    mutationFn: (name: string) =>
      projectsApi.createProject({ workspace_id: workspaceId!, name }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setNewName("");
      setShowForm(false);
    },
  });

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Выбери пространство в настройках
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Проекты</h1>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
        >
          <Plus size={16} /> Новый проект
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-indigo-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-700">Новый проект</span>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
              <X size={16} />
            </button>
          </div>
          <input
            type="text"
            placeholder="Название проекта"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && newName.trim() && createMutation.mutate(newName.trim())}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-400"
            autoFocus
          />
          <button
            onClick={() => newName.trim() && createMutation.mutate(newName.trim())}
            disabled={!newName.trim() || createMutation.isPending}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {createMutation.isPending ? "Создаю..." : "Создать"}
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Загрузка...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <FolderOpen size={48} className="mx-auto mb-3 opacity-30" />
          <p>Нет проектов. Создай первый!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((project) => {
            const projectTasks = allTasks.filter((t) => t.project_id === project.id);
            const done = projectTasks.filter((t) => t.status === "done").length;
            const total = projectTasks.length;
            const pct = total > 0 ? Math.round((done / total) * 100) : 0;

            return (
              <div
                key={project.id}
                className="bg-white rounded-xl border border-gray-100 p-4 space-y-3 hover:shadow-md transition"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: project.color }}
                  />
                  <span className="font-semibold text-gray-800">{project.name}</span>
                </div>
                <div className="text-sm text-gray-500">
                  {done}/{total} задач выполнено
                </div>
                <div className="w-full bg-gray-100 rounded-full h-1.5">
                  <div
                    className="bg-indigo-500 h-1.5 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
