export interface AdminStats {
  student_count: number;
  course_count: number;
  enrollment_count: number;
  indexed_document_count: number;
  total_chunk_count: number;
  last_ingested_at: string | null;
}

export interface AdminDocument {
  id: number;
  filename: string;
  doc_type: string;
  uploaded_at: string;
  indexed_at: string | null;
  status: "pending" | "indexing" | "indexed" | "failed";
  chunk_count: number;
}

export interface AdminStudentSummary {
  student_id: string;
  first_name: string;
  last_name: string;
  program_code: string;
  program_name: string;
  academic_status: string;
  cumulative_gpa: string | null;
  total_credits_earned: number;
}

export interface AdminCourseHistoryEntry {
  course_code: string;
  title: string;
  credits: number;
  grade: string | null;
  status: string;
}

export interface AdminTermHistory {
  term_code: string;
  term_name: string;
  term_gpa: string | null;
  courses: AdminCourseHistoryEntry[];
}

export interface AdminEligibleCourse {
  course_code: string;
  title: string;
  credits: number;
}

export interface AdminCategoryProgress {
  category_id: string;
  category_name: string;
  credits_required: number;
  credits_earned: number;
  credits_in_progress: number;
  credits_remaining: number;
  eligible_courses_not_taken: AdminEligibleCourse[];
}

export interface AdminStudentProfile {
  student_id: string;
  first_name: string;
  last_name: string;
  email: string;
  program_code: string;
  program_name: string;
  entry_term: string;
  expected_graduation_term: string;
  academic_status: string;
  advisor_name: string;
  cumulative_gpa: string | null;
  total_credits_earned: number;
}

export interface AdminStudentDetail {
  profile: AdminStudentProfile;
  terms: AdminTermHistory[];
  degree_progress: AdminCategoryProgress[];
}

export interface AdminCourse {
  course_code: string;
  title: string;
  credits: number;
  prerequisites: string[];
  categories: string[];
}

export interface AdminEnrollment {
  student_id: string;
  student_name: string;
  term_code: string;
  course_code: string;
  course_title: string;
  credits: number;
  grade: string | null;
  status: string;
}

export interface AdminEnrollmentPage {
  items: AdminEnrollment[];
  total: number;
  page: number;
  page_size: number;
}

export interface AssistantConfig {
  persona: string;
  model_provider: string;
  model_name: string;
  response_length: "brief" | "detailed";
  temperature: string;
  updated_at: string;
}
