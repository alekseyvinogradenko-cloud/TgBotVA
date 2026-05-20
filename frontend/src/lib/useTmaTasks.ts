"use client";
import { useQuery } from "@tanstack/react-query";
import { tmaApi } from "./tmaAuth";

export type TaskStatus = "todo" | "in_progress" | "done" | "cancelled";
export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface TmaTask {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  is_overdue: boolean;
  project: { id: string; name: string; color: string };
  assignee: { id: string; first_name: string; initials: string } | null;
}

export function useMyTasks(enabled: boolean) {
  return useQuery({
    queryKey: ["tma", "tasks", "mine"],
    queryFn: async (): Promise<TmaTask[]> => {
      const res = await tmaApi.get<TmaTask[]>("/tasks/mine");
      return res.data;
    },
    enabled,
    staleTime: 30_000,
  });
}
