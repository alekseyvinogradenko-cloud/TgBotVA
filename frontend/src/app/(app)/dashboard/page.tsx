"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi, type Task } from "@/lib/api";
import { TaskCard } from "@/components/TaskCard";
import { StatsCards } from "@/components/StatsCards";
import { useWorkspace } from "@/lib/useWorkspace";

export default function DashboardPage() {
  const { workspaceId } = useWorkspace();

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["tasks", workspaceId],
    queryFn: () => tasksApi.getWorkspaceTasks(workspaceId!),
    enabled: !!workspaceId,
  });

  const todo = tasks.filter((t) => t.status === "todo");
  const inProgress = tasks.filter((t) => t.status === "in_progress");
  const done = tasks.filter((t) => t.status === "done");

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center space-y-2">
          <p className="text-lg">Выбери пространство в боковом меню</p>
          <p className="text-sm">или перейди в <a href="/admin/settings" className="text-indigo-600 underline">Настройки</a></p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Дашборд</h1>
      <StatsCards todo={todo.length} inProgress={inProgress.length} done={done.length} />

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Загрузка...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Column title="К выполнению" tasks={todo} color="bg-gray-100" />
          <Column title="В работе" tasks={inProgress} color="bg-blue-50" />
          <Column title="Выполнено" tasks={done} color="bg-green-50" />
        </div>
      )}
    </div>
  );
}

function Column({ title, tasks, color }: { title: string; tasks: Task[]; color: string }) {
  return (
    <div className={`rounded-xl p-4 ${color} space-y-3`}>
      <h2 className="font-semibold text-gray-700">
        {title} <span className="text-gray-400 font-normal">({tasks.length})</span>
      </h2>
      {tasks.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-4">Пусто</p>
      ) : (
        tasks.map((task) => <TaskCard key={task.id} task={task} />)
      )}
    </div>
  );
}
