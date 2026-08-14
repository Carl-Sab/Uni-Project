import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  AdminCourse,
  AdminDocument,
  AdminEnrollmentPage,
  AdminStats,
  AdminStudentDetail,
  AdminStudentSummary,
  AssistantConfig,
} from "./adminTypes";

export function useAdminStats() {
  return useQuery({ queryKey: ["admin", "stats"], queryFn: () => api.get<AdminStats>("/api/admin/stats") });
}

export function useAdminDocuments() {
  return useQuery({
    queryKey: ["admin", "documents"],
    queryFn: () => api.get<AdminDocument[]>("/api/admin/documents"),
    // Ingestion runs in the background - poll while anything is still
    // pending/indexing so the status column updates live without a
    // manual refresh.
    refetchInterval: (query) => {
      const docs = query.state.data as AdminDocument[] | undefined;
      const stillWorking = docs?.some((d) => d.status === "pending" || d.status === "indexing");
      return stillWorking ? 1500 : false;
    },
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ file, docType }: { file: File; docType: string }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("doc_type", docType);
      return api.upload<AdminDocument>("/api/admin/documents", formData);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "documents"] }),
  });
}

export function useReindexDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post(`/api/admin/documents/${id}/reindex`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "documents"] }),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/api/admin/documents/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "documents"] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}

export function useAdminStudents() {
  return useQuery({
    queryKey: ["admin", "students"],
    queryFn: () => api.get<AdminStudentSummary[]>("/api/admin/students"),
  });
}

export function useAdminStudentDetail(studentId: string | undefined) {
  return useQuery({
    queryKey: ["admin", "students", studentId],
    queryFn: () => api.get<AdminStudentDetail>(`/api/admin/students/${studentId}`),
    enabled: !!studentId,
  });
}

export function useAdminCourses() {
  return useQuery({
    queryKey: ["admin", "courses"],
    queryFn: () => api.get<AdminCourse[]>("/api/admin/courses"),
  });
}

export function useAdminEnrollments(params: {
  studentId?: string;
  termCode?: string;
  page: number;
  pageSize: number;
}) {
  const qs = new URLSearchParams();
  if (params.studentId) qs.set("student_id", params.studentId);
  if (params.termCode) qs.set("term_code", params.termCode);
  qs.set("page", String(params.page));
  qs.set("page_size", String(params.pageSize));

  return useQuery({
    queryKey: ["admin", "enrollments", params],
    queryFn: () => api.get<AdminEnrollmentPage>(`/api/admin/enrollments?${qs.toString()}`),
  });
}

export function useAdminConfig() {
  return useQuery({
    queryKey: ["admin", "config"],
    queryFn: () => api.get<AssistantConfig>("/api/admin/config"),
  });
}

export function useUpdateAdminConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Omit<AssistantConfig, "updated_at">) =>
      api.put<AssistantConfig>("/api/admin/config", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "config"] }),
  });
}
