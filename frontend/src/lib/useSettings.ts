"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tmaApi } from "./tmaAuth";

export interface UserSettings {
  notify_morning_digest: boolean;
  notify_morning_time: string;
  notify_weekly_report: boolean;
  timezone: string;
  ai_model: string;
}

export const AI_MODELS: { value: string; label: string }[] = [
  { value: "claude-haiku-4-5-20251001", label: "Haiku 4.5 — быстрый, дешёвый" },
  { value: "claude-sonnet-4-6", label: "Sonnet 4.6 — баланс" },
  { value: "claude-opus-4-7", label: "Opus 4.7 — самый умный" },
];

export const TIMEZONES = [
  "Europe/Moscow",
  "Europe/Kiev",
  "Europe/Chisinau",
  "Europe/Minsk",
  "Asia/Almaty",
  "Asia/Tashkent",
  "Europe/London",
];

export function useSettings(enabled: boolean) {
  return useQuery({
    queryKey: ["tma", "settings"],
    queryFn: async (): Promise<UserSettings> => {
      const res = await tmaApi.get<UserSettings>("/settings");
      return res.data;
    },
    enabled,
    staleTime: 60_000,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<UserSettings>): Promise<UserSettings> => {
      const res = await tmaApi.patch<UserSettings>("/settings", patch);
      return res.data;
    },
    onSuccess: (data) => {
      qc.setQueryData(["tma", "settings"], data);
    },
  });
}
