import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL + "/api",
  headers: { "Content-Type": "application/json" },
});

// Types
export type TaskStatus = "todo" | "in_progress" | "done" | "cancelled";
export type TaskPriority = "low" | "medium" | "high" | "urgent";
export type UserRole = "owner" | "manager" | "executor" | "observer";

export interface Task {
  id: string;
  project_id: string;
  parent_id: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  subtasks?: Task[];
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  color: string;
  is_archived: boolean;
}

export interface Workspace {
  id: string;
  name: string;
  type: string;
  telegram_bot_username: string | null;
}

export interface User {
  id: string;
  telegram_id: number;
  first_name: string;
  last_name: string | null;
  telegram_username: string | null;
}

// API functions
export const tasksApi = {
  getWorkspaceTasks: (workspaceId: string, status?: TaskStatus) =>
    api.get<Task[]>(`/tasks/workspace/${workspaceId}`, { params: { status } }).then((r) => r.data),

  createTask: (data: Partial<Task>) =>
    api.post<Task>("/tasks/", data).then((r) => r.data),

  updateTask: (id: string, data: Partial<Task>) =>
    api.patch<Task>(`/tasks/${id}`, data).then((r) => r.data),

  deleteTask: (id: string) =>
    api.delete(`/tasks/${id}`),
};

export const projectsApi = {
  getWorkspaceProjects: (workspaceId: string) =>
    api.get<Project[]>(`/projects/workspace/${workspaceId}`).then((r) => r.data),

  createProject: (data: Partial<Project> & { workspace_id: string }) =>
    api.post<Project>("/projects/", data).then((r) => r.data),

  updateProject: (id: string, data: Partial<Project>) =>
    api.patch<Project>(`/projects/${id}`, data).then((r) => r.data),

  deleteProject: (id: string) =>
    api.delete(`/projects/${id}`),
};

export const workspacesApi = {
  list: () => api.get<Workspace[]>("/workspaces/").then((r) => r.data),

  create: (data: { name: string; type: string; telegram_bot_token: string; owner_telegram_id: number }) =>
    api.post<Workspace>("/workspaces/", data).then((r) => r.data),
};
