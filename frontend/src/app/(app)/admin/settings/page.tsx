"use client";
import { useQuery } from "@tanstack/react-query";
import { workspacesApi, type Workspace } from "@/lib/api";
import { useWorkspace } from "@/lib/useWorkspace";
import { CheckCircle2, Bot, Globe } from "lucide-react";

export default function SettingsPage() {
  const { workspaceId, setWorkspaceId } = useWorkspace();

  const { data: workspaces = [], isLoading } = useQuery({
    queryKey: ["workspaces"],
    queryFn: workspacesApi.list,
  });

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900">Настройки</h1>

      {/* Workspace selector */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Активное пространство</h2>
        {isLoading ? (
          <div className="text-gray-400 text-sm">Загрузка...</div>
        ) : workspaces.length === 0 ? (
          <div className="text-gray-400 text-sm">
            Нет пространств. Создай первое через API или Telegram бот.
          </div>
        ) : (
          <div className="space-y-2">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => setWorkspaceId(ws.id)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border transition text-left ${
                  workspaceId === ws.id
                    ? "border-indigo-300 bg-indigo-50"
                    : "border-gray-100 hover:border-gray-200 hover:bg-gray-50"
                }`}
              >
                <div className="flex-1">
                  <div className="font-medium text-gray-800">{ws.name}</div>
                  <div className="text-sm text-gray-400">{ws.type}</div>
                  {ws.telegram_bot_username && (
                    <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
                      <Bot size={11} />
                      @{ws.telegram_bot_username}
                    </div>
                  )}
                </div>
                {workspaceId === ws.id && (
                  <CheckCircle2 size={20} className="text-indigo-500 shrink-0" />
                )}
              </button>
            ))}
          </div>
        )}
      </section>

      {/* API info */}
      <section className="bg-white rounded-xl border border-gray-100 p-5 space-y-3">
        <h2 className="font-semibold text-gray-800">Подключение</h2>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Globe size={16} className="text-gray-400" />
          <span>API URL:</span>
          <code className="bg-gray-100 px-2 py-0.5 rounded text-xs">
            {process.env.NEXT_PUBLIC_API_URL ?? "не задан"}
          </code>
        </div>
      </section>

      {/* Register new workspace hint */}
      <section className="bg-amber-50 rounded-xl border border-amber-100 p-5 space-y-2">
        <h2 className="font-semibold text-amber-800">Добавить новое пространство</h2>
        <p className="text-sm text-amber-700">
          Зарегистрируй новый бот через BotFather и отправь запрос:
        </p>
        <pre className="bg-amber-100 rounded-lg p-3 text-xs text-amber-900 overflow-x-auto whitespace-pre-wrap">
{`POST ${process.env.NEXT_PUBLIC_API_URL ?? "<API_URL>"}/api/workspaces/
{
  "name": "Работа",
  "type": "work",
  "telegram_bot_token": "YOUR_TOKEN",
  "owner_telegram_id": YOUR_TG_ID
}`}
        </pre>
      </section>
    </div>
  );
}
