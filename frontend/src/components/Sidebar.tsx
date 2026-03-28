"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, CheckSquare, FolderOpen, Users, Settings } from "lucide-react";
import { clsx } from "clsx";
import { WorkspaceSelector } from "./WorkspaceSelector";

const nav = [
  { href: "/dashboard", label: "Дашборд", icon: LayoutDashboard },
  { href: "/tasks", label: "Задачи", icon: CheckSquare },
  { href: "/projects", label: "Проекты", icon: FolderOpen },
  { href: "/admin", label: "Команда", icon: Users },
  { href: "/admin/settings", label: "Настройки", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 bg-white border-r border-gray-100 flex flex-col py-6">
      <div className="px-4 mb-4">
        <span className="text-lg font-bold text-indigo-600">Assistant</span>
      </div>
      <WorkspaceSelector />
      <nav className="flex-1 space-y-1 px-2">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition",
              pathname === href
                ? "bg-indigo-50 text-indigo-600"
                : "text-gray-600 hover:bg-gray-50"
            )}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
