"use client";
import { useQuery } from "@tanstack/react-query";
import { tmaApi } from "./tmaAuth";

export interface Member {
  id: string;
  first_name: string;
  initials: string;
  role: string;
  is_me: boolean;
}

export function useMembers(enabled: boolean) {
  return useQuery({
    queryKey: ["tma", "members"],
    queryFn: async (): Promise<Member[]> => {
      const res = await tmaApi.get<Member[]>("/workspaces/members");
      return res.data;
    },
    enabled,
    staleTime: 60_000,
  });
}

const AVATAR_COLORS = ["#fb923c", "#06b6d4", "#a78bfa", "#f43f5e", "#22c55e", "#f59e0b"];
export function avatarColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[hash % AVATAR_COLORS.length];
}
