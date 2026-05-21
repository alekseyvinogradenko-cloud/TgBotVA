"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tmaApi } from "./tmaAuth";
import type { TaskPriority, TaskStatus } from "./useTmaTasks";

export interface TaskDetailData {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  is_overdue: boolean;
  project: { id: string; name: string; color: string };
  assignee: { id: string; first_name: string; initials: string } | null;
  subtasks: { id: string; title: string; status: TaskStatus }[];
  notes: { id: string; content: string; created_at: string }[];
}

export function useTaskDetail(taskId: string | null) {
  return useQuery({
    queryKey: ["tma", "task", taskId],
    queryFn: async (): Promise<TaskDetailData> => {
      const res = await tmaApi.get<TaskDetailData>(`/tasks/${taskId}`);
      return res.data;
    },
    enabled: !!taskId,
    staleTime: 15_000,
  });
}

function useTaskInvalidation(taskId: string | null) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["tma", "tasks", "mine"] });
    if (taskId) qc.invalidateQueries({ queryKey: ["tma", "task", taskId] });
  };
}

export function useSetStatus(taskId: string | null) {
  const invalidate = useTaskInvalidation(taskId);
  return useMutation({
    mutationFn: async (status: TaskStatus) => {
      await tmaApi.post(`/tasks/${taskId}/status`, { status });
    },
    onSuccess: invalidate,
  });
}

export function useEditTask(taskId: string | null) {
  const invalidate = useTaskInvalidation(taskId);
  return useMutation({
    mutationFn: async (patch: {
      title?: string;
      description?: string | null;
      due_date?: string | null;
      priority?: TaskPriority;
      assignee_id?: string;
    }) => {
      await tmaApi.post(`/tasks/${taskId}/update`, patch);
    },
    onSuccess: invalidate,
  });
}

export function useDeleteTask(taskId: string | null) {
  const invalidate = useTaskInvalidation(taskId);
  return useMutation({
    mutationFn: async () => {
      await tmaApi.post(`/tasks/${taskId}/delete`);
    },
    onSuccess: invalidate,
  });
}

export function useAddSubtask(taskId: string | null) {
  const invalidate = useTaskInvalidation(taskId);
  return useMutation({
    mutationFn: async (title: string) => {
      await tmaApi.post(`/tasks/${taskId}/subtask`, { title });
    },
    onSuccess: invalidate,
  });
}

export function useAddNote(taskId: string | null) {
  const invalidate = useTaskInvalidation(taskId);
  return useMutation({
    mutationFn: async (content: string) => {
      await tmaApi.post(`/tasks/${taskId}/note`, { content });
    },
    onSuccess: invalidate,
  });
}
