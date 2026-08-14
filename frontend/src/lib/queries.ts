import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type {
  Appointment,
  CatalogueCourse,
  CategoryProgress,
  ChatMessage,
  ChatSessionSummary,
  Eligibility,
  Profile,
  ScheduleItem,
  TermHistory,
} from "./types";

export function useProfile() {
  return useQuery({ queryKey: ["profile"], queryFn: () => api.get<Profile>("/api/me") });
}

export function useSchedule() {
  return useQuery({
    queryKey: ["schedule"],
    queryFn: () => api.get<ScheduleItem[]>("/api/me/schedule"),
  });
}

export function useCourseHistory() {
  return useQuery({
    queryKey: ["courses"],
    queryFn: () => api.get<TermHistory[]>("/api/me/courses"),
  });
}

export function useDegreeProgress() {
  return useQuery({
    queryKey: ["degree-progress"],
    queryFn: () => api.get<CategoryProgress[]>("/api/me/degree-progress"),
  });
}

export function useCatalogue() {
  return useQuery({
    queryKey: ["catalogue"],
    queryFn: () => api.get<CatalogueCourse[]>("/api/courses"),
  });
}

export function useEligibility(courseCode: string, enabled: boolean) {
  return useQuery({
    queryKey: ["eligibility", courseCode],
    queryFn: () => api.get<Eligibility>(`/api/me/eligibility/${encodeURIComponent(courseCode)}`),
    enabled,
    staleTime: 60_000,
  });
}

export function useAppointments() {
  return useQuery({
    queryKey: ["appointments"],
    queryFn: () => api.get<Appointment[]>("/api/me/appointments"),
  });
}

export function useApproveAppointment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api.post<Appointment>(`/api/me/appointments/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["appointments"] }),
  });
}

export function useChatSessions() {
  return useQuery({
    queryKey: ["chat-sessions"],
    queryFn: () => api.get<ChatSessionSummary[]>("/api/me/chats"),
  });
}

export function useChatHistory(sessionId: number | null) {
  return useQuery({
    queryKey: ["chat-history", sessionId],
    queryFn: () => api.get<ChatMessage[]>(`/api/me/chats/${sessionId}`),
    enabled: sessionId !== null,
  });
}
