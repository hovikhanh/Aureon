"use client";
/** SCR-51/52 data hooks (T-617F) — EP-ORG-24 tree, EP-ORG-21 history, lists for pickers, mutations. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";

export type DepartmentOut = Api.DepartmentOut;
export type EmployeeAssignmentOut = Api.EmployeeAssignmentOut;
export type OrgTreeOut = Api.OrgTreeOut;
export type PositionOut = Api.PositionOut;
export type TeamOut = Api.TeamOut;
export type TreeDept = OrgTreeOut["departments"][number];
export type TreeMember = TreeDept["members"][number];

/** "Today" as the API sees it: EP-ORG-* compare `valid_from` / `as_of` with the UTC date
 *  (`hr/services/org_service._today`). A local date would be "future" between 00:00–07:00 ICT. */
export const todayIso = (): string => new Date().toISOString().slice(0, 10);

export function useOrgTree(asOf: string) {
  return useQuery({
    queryKey: qk.orgTree(asOf),
    queryFn: ({ signal }) => apiRequest<OrgTreeOut>("/org/tree", { query: { as_of: asOf }, signal }),
  });
}

export function useAssignmentHistory(employeeId: string | null) {
  return useQuery({
    queryKey: qk.assignments({ employee_id: employeeId }),
    enabled: Boolean(employeeId),
    queryFn: ({ signal }) => apiRequest<EmployeeAssignmentOut[]>("/org/assignments", { query: { employee_id: employeeId, sort_by: "valid_from", limit: 100 }, signal }),
  });
}

export function useDepartments() {
  return useQuery({
    queryKey: qk.departments(),
    queryFn: ({ signal }) => apiRequest<DepartmentOut[]>("/hr/departments", { query: { limit: 100 }, signal }),
  });
}

export function useTeams(departmentId: string | null) {
  return useQuery({
    queryKey: qk.teams(departmentId),
    enabled: Boolean(departmentId),
    queryFn: ({ signal }) => apiRequest<TeamOut[]>("/org/teams", { query: { department_id: departmentId, limit: 100 }, signal }),
  });
}

export function usePositions(departmentId: string | null, q = "") {
  return useQuery({
    queryKey: qk.positions({ department_id: departmentId, q }),
    queryFn: ({ signal }) => apiRequest<PositionOut[]>("/org/positions", { query: { department_id: departmentId, q: q || undefined, limit: 100 }, signal }),
  });
}

/** Any org mutation → refetch the tree, pickers and positions (structure changed). */
export function useOrgMutation<TVars>(fn: (v: TVars) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org"] }),
  });
}
