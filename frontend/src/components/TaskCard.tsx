"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import { tasksApi, type Task, type TaskStatus } from "@/lib/api";
import { CheckCircle2, Circle, Clock, AlertCircle } from "lucide-react";

const priorityConfig = {
  low: { label: "Низкий", color: "text-green-500", dot: "bg-green-400" },
  medium: { label: "Средний", color: "text-yellow-500", dot: "bg-yellow-400" },
  high: { label: "Высокий", color: "text-orange-500", dot: "bg-orange-400" },
  urgent: { label: "Срочный", color: "text-red-500", dot: "bg-red-400" },
};

export function TaskCard({ task }: { task: Task }) {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (status: TaskStatus) => tasksApi.updateTask(task.id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const priority = priorityConfig[task.priority];
  const isOverdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== "done";

  return (
    <div className="bg-white rounded-lg p-3 shadow-sm border border-gray-100 space-y-2 hover:shadow-md transition">
      <div className="flex items-start gap-2">
        <button
          onClick={() => mutation.mutate(task.status === "done" ? "todo" : "done")}
          className="mt-0.5 shrink-0 text-gray-400 hover:text-green-500 transition"
        >
          {task.status === "done" ? (
            <CheckCircle2 size={18} className="text-green-500" />
          ) : (
            <Circle size={18} />
          )}
        </button>
        <span className={`text-sm font-medium ${task.status === "done" ? "line-through text-gray-400" : "text-gray-800"}`}>
          {task.title}
        </span>
      </div>

      <div className="flex items-center gap-3 pl-6">
        <span className={`flex items-center gap-1 text-xs ${priority.color}`}>
          <span className={`w-2 h-2 rounded-full ${priority.dot}`} />
          {priority.label}
        </span>

        {task.due_date && (
          <span className={`flex items-center gap-1 text-xs ${isOverdue ? "text-red-500" : "text-gray-400"}`}>
            {isOverdue ? <AlertCircle size={12} /> : <Clock size={12} />}
            {format(new Date(task.due_date), "d MMM", { locale: ru })}
          </span>
        )}

        {task.status !== "done" && task.status !== "in_progress" && (
          <button
            onClick={() => mutation.mutate("in_progress")}
            className="ml-auto text-xs text-blue-500 hover:text-blue-700"
          >
            В работу
          </button>
        )}
      </div>
    </div>
  );
}
