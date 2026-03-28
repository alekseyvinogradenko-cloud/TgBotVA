"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useWorkspace } from "@/lib/useWorkspace";
import { Users, Crown, Briefcase, Eye } from "lucide-react";

interface Member {
  id: string;
  role: string;
  user: {
    id: string;
    first_name: string;
    last_name: string | null;
    telegram_username: string | null;
  };
}

const ROLE_CONFIG = {
  owner: { label: "Владелец", icon: Crown, color: "text-amber-500 bg-amber-50" },
  manager: { label: "Менеджер", icon: Briefcase, color: "text-indigo-500 bg-indigo-50" },
  executor: { label: "Исполнитель", icon: Users, color: "text-gray-500 bg-gray-50" },
  observer: { label: "Наблюдатель", icon: Eye, color: "text-gray-400 bg-gray-50" },
};

export default function AdminPage() {
  const { workspaceId } = useWorkspace();

  const { data: members = [], isLoading } = useQuery({
    queryKey: ["members", workspaceId],
    queryFn: () => api.get<Member[]>(`/workspaces/${workspaceId}/members`).then((r) => r.data),
    enabled: !!workspaceId,
  });

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Выбери пространство в настройках
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Команда</h1>
        <span className="text-sm text-gray-400">{members.length} участников</span>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Загрузка...</div>
      ) : members.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Users size={48} className="mx-auto mb-3 opacity-30" />
          <p>Нет участников. Участники добавляются автоматически при старте бота.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 divide-y divide-gray-50">
          {members.map((m) => {
            const roleConf = ROLE_CONFIG[m.role as keyof typeof ROLE_CONFIG] ?? ROLE_CONFIG.executor;
            const Icon = roleConf.icon;
            const name = [m.user.first_name, m.user.last_name].filter(Boolean).join(" ");
            return (
              <div key={m.id} className="flex items-center gap-4 p-4">
                <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-semibold shrink-0">
                  {name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-800">{name}</div>
                  {m.user.telegram_username && (
                    <div className="text-sm text-gray-400">@{m.user.telegram_username}</div>
                  )}
                </div>
                <span className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${roleConf.color}`}>
                  <Icon size={12} />
                  {roleConf.label}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className="bg-blue-50 rounded-xl p-4 text-sm text-blue-700">
        💡 Участники добавляются автоматически когда пишут боту команду /start
      </div>
    </div>
  );
}
