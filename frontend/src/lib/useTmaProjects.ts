"use client";
import { useQuery } from "@tanstack/react-query";
import { tmaApi } from "./tmaAuth";

export interface TmaProject {
  id: string;
  name: string;
  color: string;
  description: string | null;
}

export function useMyProjects(enabled: boolean) {
  return useQuery({
    queryKey: ["tma", "projects", "mine"],
    queryFn: async (): Promise<TmaProject[]> => {
      const res = await tmaApi.get<TmaProject[]>("/projects/mine");
      return res.data;
    },
    enabled,
    staleTime: 60_000,
  });
}
