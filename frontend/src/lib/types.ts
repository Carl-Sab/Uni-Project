export interface Profile {
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

export interface ScheduleItem {
  course_code: string;
  title: string;
  credits: number;
  days: string;
  start_time: string;
  end_time: string;
  room: string;
  instructor: string;
}

export interface CourseHistoryEntry {
  course_code: string;
  title: string;
  credits: number;
  grade: string | null;
  status: string;
}

export interface TermHistory {
  term_code: string;
  term_name: string;
  term_gpa: string | null;
  courses: CourseHistoryEntry[];
}

export interface EligibleCourse {
  course_code: string;
  title: string;
  credits: number;
}

export interface CategoryProgress {
  category_id: string;
  category_name: string;
  credits_required: number;
  credits_earned: number;
  credits_in_progress: number;
  credits_remaining: number;
  eligible_courses_not_taken: EligibleCourse[];
}

export interface PrereqCheck {
  prerequisite_course_code: string;
  satisfied: boolean;
  grade_earned: string | null;
}

export interface Eligibility {
  course_code: string;
  eligible: boolean;
  prerequisites: PrereqCheck[];
}

export interface CatalogueCourse {
  course_code: string;
  title: string;
  credits: number;
  description: string;
  prerequisites: string[];
}

export interface ChatSessionSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface Appointment {
  id: number;
  status: "pending" | "approved" | "declined";
  reason: string;
  preferred_time: string;
  created_at: string;
}
