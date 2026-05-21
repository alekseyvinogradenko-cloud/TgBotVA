"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { tmaApi } from "./tmaAuth";
import type { TaskPriority, TmaTask } from "./useTmaTasks";

export interface ParseResult {
  title: string;
  description: string | null;
  due_date: string | null;
  priority: TaskPriority;
  project_hint: string | null;
}

export function useParseTask() {
  return useMutation({
    mutationFn: async (text: string): Promise<ParseResult> => {
      const res = await tmaApi.post<ParseResult>("/tasks/parse", { text });
      return res.data;
    },
  });
}

export interface CreateTaskInput {
  project_id: string;
  title: string;
  description?: string | null;
  due_date?: string | null;
  priority: TaskPriority;
  assignee_id?: string | null;
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateTaskInput): Promise<TmaTask> => {
      const res = await tmaApi.post<TmaTask>("/tasks/create", input);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tma", "tasks", "mine"] });
    },
  });
}
