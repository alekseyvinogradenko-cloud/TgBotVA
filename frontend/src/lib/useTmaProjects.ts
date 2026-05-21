"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tmaApi } from "./tmaAuth";

export interface TmaProject {
  id: string;
  name: string;
  color: string;
  description: string | null;
  is_archived: boolean;
}

export function useMyProjects(enabled: boolean, includeArchived = false) {
  return useQuery({
    queryKey: ["tma", "projects", "mine", includeArchived],
    queryFn: async (): Promise<TmaProject[]> => {
      const res = await tmaApi.get<TmaProject[]>("/projects/mine", {
        params: { include_archived: includeArchived },
      });
      return res.data;
    },
    enabled,
    staleTime: 60_000,
  });
}

function useProjectsInvalidation() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["tma", "projects"] });
}

export function useCreateProject() {
  const invalidate = useProjectsInvalidation();
  return useMutation({
    mutationFn: async (input: { name: string; color: string }): Promise<TmaProject> => {
      const res = await tmaApi.post<TmaProject>("/projects/create", input);
      return res.data;
    },
    onSuccess: invalidate,
  });
}

export function useArchiveProject() {
  const invalidate = useProjectsInvalidation();
  return useMutation({
    mutationFn: async ({ id, archived }: { id: string; archived: boolean }) => {
      await tmaApi.post(`/projects/${id}/archive`, { archived });
    },
    onSuccess: invalidate,
  });
}
