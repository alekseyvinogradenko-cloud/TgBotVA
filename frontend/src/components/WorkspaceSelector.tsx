"use client";
import { useQuery } from "@tanstack/react-query";
import { workspacesApi } from "@/lib/api";
import { useWorkspace } from "@/lib/useWorkspace";
import { ChevronDown } from "lucide-react";
import { useState, useRef, useEffect } from "react";

export function WorkspaceSelector() {
  const { workspaceId, setWorkspaceId } = useWorkspace();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data: workspaces = [] } = useQuery({
    queryKey: ["workspaces"],
    queryFn: workspacesApi.list,
  });

  const current = workspaces.find((w) => w.id === workspaceId);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative px-2 mb-4">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50 hover:bg-gray-100 transition text-sm"
      >
        <span className="font-medium text-gray-700 truncate">
          {current?.name ?? "Выбрать пространство"}
        </span>
        <ChevronDown size={14} className="text-gray-400 shrink-0 ml-1" />
      </button>

      {open && (
        <div className="absolute left-2 right-2 top-full mt-1 bg-white border border-gray-100 rounded-lg shadow-lg z-50 overflow-hidden">
          {workspaces.length === 0 ? (
            <div className="px-3 py-2 text-xs text-gray-400">Нет пространств</div>
          ) : (
            workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => { setWorkspaceId(ws.id); setOpen(false); }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 transition ${
                  ws.id === workspaceId ? "text-indigo-600 font-medium" : "text-gray-700"
                }`}
              >
                {ws.name}
                <span className="text-xs text-gray-400 ml-1">({ws.type})</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
