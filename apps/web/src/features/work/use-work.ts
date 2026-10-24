"use client";
/** SCR-42/43/55/56/57 data hooks (T-625F) — one query per widget; contract = 10 §7.2.2. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";

export type TaskOut = Api.TaskOut;
export type TaskCreate = Api.TaskCreate;
export type TaskUpdate = Api.TaskUpdate;
export type TaskDependenciesOut = Api.TaskDependenciesOut;
export type TaskBriefOut = Api.TaskBriefOut;
export type ProjectOut = Api.ProjectOut;
export type ProjectDetailOut = Api.ProjectDetailOut;
export type MilestoneOut = Api.MilestoneOut;
export type WorkloadOut = Api.WorkloadOut;
export type ApprovalRequestOut = Api.ApprovalRequestOut;
export type ApprovalDetailOut = Api.ApprovalDetailOut;
export type OrgTreeOut = Api.OrgTreeOut;
export type TreeMember = OrgTreeOut["departments"][number]["members"][number];

type Q = Record<string, string | number | boolean | null | undefined>;
type TaskQuery = { [k: string]: string | number | boolean | null | undefined | readonly string[] };

/** EP-TASK-01 accepts `status` repeated; the api-client query builder keeps one value per key. */
/** `/work/tasks?…` with a repeated `status` (buildUrl keeps one value per key → whole query in the path). */
export function taskPath(params: TaskQuery): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries({ limit: 100, ...params })) {
    if (Array.isArray(v)) for (const x of v) qs.append(k, String(x));
    else if (v !== undefined && v !== null && String(v) !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `/work/tasks?${s}` : "/work/tasks";
}

export function useTasks(params: TaskQuery, enabled = true) {
  return useQuery({
    queryKey: qk.tasks(params),
    enabled,
    queryFn: ({ signal }) => {
      return apiRequest<TaskOut[]>(taskPath(params), { signal });
    },
  });
}

export function useTask(id: string | null) {
  return useQuery({
    queryKey: qk.task(id ?? ""),
    enabled: Boolean(id),
    queryFn: ({ signal }) => apiRequest<TaskOut>(`/work/tasks/${id}`, { signal }).then((r) => r.data),
  });
}

export function useDependencies(id: string | null) {
  return useQuery({
    queryKey: qk.taskDependencies(id ?? ""),
    enabled: Boolean(id),
    queryFn: ({ signal }) => apiRequest<TaskDependenciesOut>(`/work/tasks/${id}/dependencies`, { signal }).then((r) => r.data),
  });
}

export interface AuditRow { id: string; occurred_at: string; action: string; actor_role: string | null; why: string | null }
/** "Lịch sử" tab: EP-52 audit filtered by `target_id` (needs `platform:read`; otherwise not shown). */
export function useHistory(id: string | null, enabled: boolean) {
  return useQuery({
    queryKey: qk.taskHistory(id ?? ""),
    enabled: Boolean(id) && enabled,
    queryFn: ({ signal }) => apiRequest<AuditRow[]>("/platform/audit-logs", { query: { target_id: id, limit: 50 }, signal }).then((r) => r.data),
  });
}

export function useProjects(params: Q) {
  return useQuery({
    queryKey: qk.projects(params),
    queryFn: ({ signal }) => apiRequest<ProjectOut[]>("/work/projects", { query: { limit: 100, ...params }, signal }),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: qk.project(id),
    queryFn: ({ signal }) => apiRequest<ProjectDetailOut>(`/work/projects/${id}`, { signal }).then((r) => r.data),
  });
}

export function useWorkload(params: Q) {
  return useQuery({
    queryKey: qk.workload(params),
    queryFn: ({ signal }) => apiRequest<WorkloadOut>("/work/workload", { query: params, signal }).then((r) => r.data),
  });
}

export function useApprovals(params: Q, enabled = true) {
  return useQuery({
    queryKey: qk.approvals(params),
    enabled,
    queryFn: ({ signal }) => apiRequest<ApprovalRequestOut[]>("/workflow/approval-requests", { query: { assigned_to: "me", limit: 100, ...params }, signal }),
  });
}

export function useApproval(id: string | null) {
  return useQuery({
    queryKey: qk.approval(id ?? ""),
    enabled: Boolean(id),
    queryFn: ({ signal }) => apiRequest<ApprovalDetailOut>(`/workflow/approval-requests/${id}`, { signal }).then((r) => r.data),
  });
}

/** Members for names / pickers (EP-ORG-24, `hr:read` level 2 — R-DEC-44). 403 → caller falls back to ids. */
export function useMembers(enabled: boolean) {
  return useQuery({
    queryKey: ["org", "tree", "members"],
    enabled,
    retry: false,
    staleTime: 5 * 60_000,
    queryFn: ({ signal }) => apiRequest<OrgTreeOut>("/org/tree", { signal }).then((r) => r.data.departments.flatMap((d) => d.members.map((m) => ({ ...m, department_id: d.id, department_name: d.name })))),
  });
}
export type Member = TreeMember & { department_id: string; department_name: string };

/** Any work mutation → refetch tasks, projects, workload, approvals. */
export function useWorkMutation<TVars, TOut = unknown>(fn: (v: TVars) => Promise<TOut>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSettled: () => Promise.all([qc.invalidateQueries({ queryKey: ["work"] }), qc.invalidateQueries({ queryKey: ["workflow"] })]),
  });
}

export const patchTask = (t: Pick<TaskOut, "id" | "version">, body: TaskUpdate) =>
  apiRequest<TaskOut>(`/work/tasks/${t.id}`, { method: "PATCH", body: { ...body, version: t.version } }).then((r) => r.data);
