"use client";
import { useState, useEffect } from "react";

export function useWorkspace() {
  const [workspaceId, setWorkspaceIdState] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("workspace_id");
    if (stored) setWorkspaceIdState(stored);
  }, []);

  const setWorkspaceId = (id: string) => {
    localStorage.setItem("workspace_id", id);
    setWorkspaceIdState(id);
  };

  return { workspaceId, setWorkspaceId };
}
