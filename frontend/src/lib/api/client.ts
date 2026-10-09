import type { ApiError, BrandSettings, LoginResponse, UserMe } from "./schema";

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Program = {
  id: string;
  title: string;
  slug: string;
  summary: string;
  status: string;
  category: string;
  default_currency: string;
};

export type Cohort = {
  id: string;
  program: string | null;
  program_title: string | null;
  name: string;
  slug: string;
  status: string;
  capacity: number;
  application_fee_kobo: number | null;
  public_apply_path: string;
};

export type ClassItem = {
  id: string;
  cohort: string;
  cohort_name: string;
  name: string;
  slug: string;
  status: string;
  capacity: number;
  order: number;
};

export type Subject = {
  id: string;
  title: string;
  subtitle: string;
  slug: string;
  status: string;
  level: string;
  category: string;
  subcategory?: string;
  language?: string;
  description_json?: Record<string, unknown>;
  intended_learners?: { learn?: string[]; requirements?: string[]; audience?: string[] };
  welcome_message?: string;
  completion_message?: string;
  pricing?: Record<string, unknown>;
  settings?: Record<string, unknown>;
  promo_video?: string;
  cover_image_url?: string | null;
  topic_count: number;
};

export type Topic = {
  id: string;
  subject: string;
  title: string;
  objective_text: string;
  order: number;
  is_published: boolean;
  subtopic_count: number;
};

export type SubtopicContent = {
  id: string;
  content_type: string;
  title: string;
  body_json: Record<string, unknown>;
  external_url: string;
  mime_type: string;
  size_bytes: number;
  processing_status: string;
  duration_s: number;
  thumbnail_url: string;
  metadata: Record<string, unknown>;
  file_url: string | null;
  preview_url: string | null;
  video_asset?: {
    id: string;
    provider: string;
    playback_id: string;
    duration_s: number;
    status: string;
  } | null;
};

export type SubtopicResource = {
  id: string;
  kind: string;
  title: string;
  url: string;
  order: number;
  download_allowed: boolean;
  file_url: string | null;
};

export type Subtopic = {
  id: string;
  topic: string;
  title: string;
  order: number;
  kind: string;
  is_published: boolean;
  is_free_preview: boolean;
  estimated_time_s: number;
  min_time_s: number;
  require_full_watch?: boolean;
  has_content?: boolean;
  content?: SubtopicContent | null;
  resources?: SubtopicResource[];
};

export type CurriculumTopic = {
  id: string;
  title: string;
  objective_text: string;
  order: number;
  is_published: boolean;
  subtopics: {
    id: string;
    title: string;
    order: number;
    kind: string;
    is_published: boolean;
    is_free_preview: boolean;
    estimated_time_s: number;
    min_time_s: number;
    has_content: boolean;
    content_type: string | null;
    content_status: string | null;
    resource_count: number;
  }[];
};

export type SubjectChecklist = {
  status: string;
  items: Record<string, boolean>;
  required: string[];
  missing: string[];
  warnings: string[];
  progress: { completed: number; total: number };
  stats: { topics: number; subtopics: number; with_content: number; video_minutes: number };
  can_publish: boolean;
};

export type ClassSubjectLink = {
  id: string;
  class_ref: string;
  subject: string;
  subject_title: string;
  subject_status: string;
  order: number;
  mode: string;
};

export type GatewaySettings = {
  mode: "test" | "live";
  public_key_masked: string;
  public_key_set: boolean;
  secret_key_set: boolean;
  default_currency: string;
  channels: {
    card: boolean;
    bank: boolean;
    ussd: boolean;
    transfer: boolean;
    mobile_money: boolean;
  };
  webhook_url: string;
  last_tested_at: string | null;
  last_test_ok: boolean | null;
};

export type ApplicationFeeSettings = {
  default_amount_kobo: number;
  default_amount_naira: number;
  is_free: boolean;
  refundable_policy: Record<string, unknown>;
  fee_required_before_admit: boolean;
  waiver_codes: unknown[];
};

export type PublicCohort = Cohort & {
  description?: string;
  application_fee_kobo: number;
  classes: ClassItem[];
};

export type ApplicationItem = {
  id: string;
  cohort: string;
  cohort_name: string;
  cohort_slug: string;
  applicant_email: string;
  applicant_name: string;
  phone: string;
  data: Record<string, unknown>;
  status: string;
  submitted_at: string;
  fee_invoice: string | null;
  fee_invoice_status: string | null;
  fee_amount_kobo: number | null;
  fee_paid_at: string | null;
  admitted_class_ids: string[];
  admissions?: { class_id: string; class_name: string; admitted_at: string }[];
};

export type EnrollmentItem = {
  id: string;
  class_ref: string;
  class_name: string;
  cohort: string;
  cohort_name: string;
  status: string;
  enrolled_at: string;
};

export type LearningSubjectCard = {
  subject_id: string;
  subject_slug: string;
  title: string;
  subtitle: string;
  cover_image_url: string | null;
  level: string;
  class_id: string;
  class_name: string;
  cohort_name: string;
  percent: number;
  continue_subtopic_id: string | null;
  last_accessed_at: string | null;
};

export type LearningClassGroup = {
  enrollment_id: string;
  class_id: string;
  class_name: string;
  cohort_name: string;
  status: string;
  enrolled_at: string;
  subjects: LearningSubjectCard[];
};

export type SubjectLanding = {
  id: string;
  slug: string;
  title: string;
  subtitle: string;
  description_json: Record<string, unknown>;
  language: string;
  level: string;
  category: string;
  intended_learners: { learn?: string[]; requirements?: string[]; audience?: string[] };
  promo_video: string;
  cover_image_url: string | null;
  instructors: { id: string; name: string; email: string }[];
  has_access: boolean;
  percent: number;
  continue_subtopic_id: string | null;
  curriculum: {
    id: string;
    title: string;
    objective_text: string;
    subtopic_count: number;
    total_time_s: number;
    subtopics: {
      id: string;
      title: string;
      kind: string;
      estimated_time_s: number;
      is_free_preview: boolean;
      content_type: string | null;
      completed: boolean;
    }[];
  }[];
  updated_at: string;
};

export type PlayerOutline = {
  subject_id: string;
  title: string;
  percent: number;
  completed_count: number;
  total_count: number;
  topics: {
    id: string;
    title: string;
    completed_count: number;
    total_count: number;
    total_time_s: number;
    subtopics: {
      id: string;
      title: string;
      kind: string;
      estimated_time_s: number;
      min_time_s: number;
      content_type: string | null;
      completed: boolean;
      time_spent_s: number;
      locked: boolean;
      lock_reason: string;
      is_free_preview: boolean;
      resource_count: number;
    }[];
  }[];
};

export type SubtopicViewer = {
  subtopic: {
    id: string;
    title: string;
    kind: string;
    description_json: Record<string, unknown>;
    estimated_time_s: number;
    min_time_s: number;
    require_full_watch: boolean;
    is_free_preview: boolean;
  };
  subject: { id: string; title: string; slug: string; description_json: Record<string, unknown> };
  progress: {
    status: string;
    percent: number;
    time_spent_s: number;
    completed: boolean;
    min_time_s: number;
    can_complete: boolean;
  };
  content: {
    content_type: string;
    title: string;
    body_json: Record<string, unknown>;
    external_url: string;
    processing_status: string;
    duration_s: number;
    file_url: string | null;
    preview_url: string | null;
    playback?: { playback_id: string; token: string | null; status: string } | null;
    video_asset_id?: string;
  } | null;
  resources: {
    id: string;
    title: string;
    kind: string;
    url: string;
    file_url: string | null;
    download_allowed: boolean;
  }[];
  video_progress: {
    last_position_s: number;
    resume_position_s: number;
    furthest_position_s: number;
    watched_pct: number;
    playback_rate: number;
  } | null;
  prev_subtopic_id: string | null;
  next_subtopic_id: string | null;
};

export type QAQuestion = {
  id: string;
  title: string;
  body: string;
  upvote_count: number;
  is_resolved: boolean;
  author_name: string;
  subtopic: string | null;
  answers: { id: string; body: string; is_instructor: boolean; author_name: string; created_at: string }[];
  created_at: string;
};

export type LearningNote = {
  id: string;
  subtopic: string;
  body: string;
  timestamp_s: number | null;
  created_at: string;
  updated_at: string;
};

export type QuizQuestion = {
  id: string;
  prompt: string;
  question_type: string;
  choices: { id: string; text: string }[];
  correct_answer?: Record<string, unknown>;
  order: number;
  points: number;
};

export type QuizDetail = {
  id: string;
  subtopic_id: string;
  title: string;
  instructions_json: Record<string, unknown>;
  settings: Record<string, unknown>;
  points_total: number;
  release_scores: boolean;
  questions: QuizQuestion[];
};

export type QuizAttempt = {
  id: string;
  quiz_id: string;
  number: number;
  status: string;
  started_at: string;
  deadline_at: string | null;
  submitted_at: string | null;
  score: number | null;
  auto_score: number | null;
  max_score: number;
  released?: boolean;
};

export type QuizAttemptReview = {
  id: string;
  quiz_id: string;
  status: string;
  number: number;
  submitted_at: string | null;
  released: boolean;
  score?: number | null;
  max_score?: number;
  auto_score?: number | null;
  message?: string;
  responses?: {
    question_id: string;
    prompt: string;
    question_type: string;
    points: number;
    answer: Record<string, unknown>;
    score: number | null;
    is_correct: boolean | null;
    correct_answer?: Record<string, unknown>;
    choices: { id: string; text: string }[];
  }[];
};

export type GradingQueueItem = {
  submission_id: string;
  assignment_id: string;
  assignment_title: string;
  subtopic_id: string;
  student_id: string;
  student_email: string;
  student_name: string;
  submitted_at: string | null;
  version: number;
  text: string;
  link: string;
  points: number;
  rubric: { id: string; title: string; criteria: { id: string; title: string; max_points?: number }[] } | null;
  class_id: string | null;
};

export type SubmissionGradeResult = {
  id: string;
  submission_id: string;
  rubric_scores: Record<string, unknown>;
  raw_score: number;
  penalty: number;
  final_score: number;
  feedback_json: Record<string, unknown>;
  graded_at: string | null;
  released_at: string | null;
};

export type GradebookPayload = {
  class_id: string;
  class_name: string;
  subject_ids: string[];
  columns: { item_type: string; item_id: string; title: string; max_score: number }[];
  students: {
    user_id: string;
    email: string;
    name: string;
    enrollment_id: string;
    grades: Record<string, { score: number | null; max_score: number; released: boolean; source: string }>;
  }[];
};

export type ReleasedGrade = {
  id: string;
  item_type: string;
  item_id: string;
  title: string;
  score: number | null;
  max_score: number;
  subject_id: string | null;
  subtopic_id: string | null;
};

export type CertificateTemplate = {
  id: string;
  name: string;
  slug: string;
  status: string;
  orientation: string;
  page_size: string;
  page_custom: Record<string, unknown>;
  current_version: string | null;
  current_version_no: number | null;
  current_design: Record<string, unknown> | null;
  last_previewed_at: string | null;
  created_at: string;
  updated_at: string;
  versions?: {
    id: string;
    version_no: number;
    design: Record<string, unknown>;
    note: string;
    is_published: boolean;
    created_at: string;
  }[];
};

export type CertificateIssueRule = {
  id: string;
  name: string;
  template: string;
  template_name: string;
  class_ref: string | null;
  class_name: string | null;
  subject: string | null;
  subject_title: string | null;
  criteria: {
    min_completion_pct?: number;
    fees_cleared?: boolean;
    manual_approval?: boolean;
  };
  auto_issue: boolean;
  valid_for_days: number | null;
  numbering_pattern: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type IssuedCertificate = {
  id: string;
  code: string;
  enrollment: string;
  template_version: string;
  issue_rule: string | null;
  subject: string | null;
  issued_at: string;
  issued_by: string | null;
  status: string;
  revoked_reason: string;
  revoked_at: string | null;
  expires_at: string | null;
  data_snapshot: Record<string, unknown>;
  holder_name: string;
  class_title: string;
  subject_title: string;
  template_name: string;
  verify_url: string;
};

export type CertificateVerifyResult = {
  code: string;
  status: string;
  holder_name: string;
  cohort_title?: string;
  program_title: string;
  class_title: string;
  subject_title: string;
  issue_date: string;
  org_name: string;
  revoked_reason: string;
  verify_url: string;
  json_ld: Record<string, unknown>;
};

export type PayInitResponse = {
  reference: string;
  authorization_url: string;
  access_code: string;
  public_key: string;
  amount_minor: number;
  currency: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
  headers?: Record<string, string>;
  /** Internal: already retried after refresh */
  _retry?: boolean;
};

function isAuthEndpoint(path: string) {
  return (
    path.startsWith("/api/v1/auth/login") ||
    path.startsWith("/api/v1/auth/register") ||
    path.startsWith("/api/v1/auth/refresh") ||
    path.startsWith("/api/v1/auth/password") ||
    path.startsWith("/api/v1/auth/logout")
  );
}

function isTokenInvalidError(status: number, err: ApiError) {
  if (status === 401) return true;
  const code = (err.code || "").toLowerCase();
  const message = (err.message || "").toLowerCase();
  return (
    code === "unauthorized" ||
    code === "token_not_valid" ||
    message.includes("token not valid") ||
    message.includes("token is invalid") ||
    message.includes("token has expired") ||
    message.includes("authentication credentials were not provided") ||
    message.includes("given token not valid for any token type")
  );
}

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: "{}",
          credentials: "include",
        });
        const data = (await res.json().catch(() => ({}))) as LoginResponse | ApiError;
        if (!res.ok) {
          accessToken = null;
          return null;
        }
        const next = (data as LoginResponse).access;
        accessToken = next;
        return next;
      } catch {
        accessToken = null;
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function forceLoginRedirect(message?: string) {
  accessToken = null;
  if (typeof window === "undefined") return;
  const { notifySessionExpired, isAuthPublicPath, loginRedirectUrl } = await import(
    "@/lib/auth/session"
  );
  const path = window.location.pathname;
  if (isAuthPublicPath(path)) return;
  notifySessionExpired(message || "Session expired. Please sign in again.");
  window.location.assign(loginRedirectUrl());
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers ?? {}),
  };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.auth !== false && accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    credentials: "include",
  });

  const data = (await res.json().catch(() => ({}))) as T | ApiError;
  if (res.ok) return data as T;

  const err = data as ApiError;
  const wantsAuth = options.auth !== false;
  const canRetry = wantsAuth && !options._retry && !isAuthEndpoint(path);

  if (canRetry && isTokenInvalidError(res.status, err)) {
    const next = await refreshAccessToken();
    if (next) {
      return request<T>(path, { ...options, _retry: true });
    }
    await forceLoginRedirect(err.message);
  }

  throw err;
}

function listPath(base: string, query?: Record<string, string | undefined>) {
  const params = new URLSearchParams();
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v) params.set(k, v);
    }
  }
  const q = params.toString();
  return q ? `${base}?${q}` : base;
}

export const api = {
  health: () => request<{ status: string }>("/api/v1/health/", { auth: false }),
  brand: () => request<BrandSettings>("/api/v1/settings/brand/", { auth: false }),
  login: (email: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),
  register: (payload: {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) =>
    request<LoginResponse>("/api/v1/auth/register", {
      method: "POST",
      body: payload,
      auth: false,
    }),
  me: () => request<UserMe>("/api/v1/auth/me"),
  refresh: () =>
    request<LoginResponse>("/api/v1/auth/refresh", {
      method: "POST",
      body: {},
      auth: false,
    }),
  logout: () => request<{ detail: string }>("/api/v1/auth/logout", { method: "POST", body: {} }),
  passwordForgot: (email: string) =>
    request<{ detail: string }>("/api/v1/auth/password/forgot", {
      method: "POST",
      body: { email },
      auth: false,
    }),

  listPrograms: () => request<Paginated<Program>>("/api/v1/programs/"),
  createProgram: (body: Partial<Program> & { title: string }) =>
    request<Program>("/api/v1/programs/", { method: "POST", body }),
  getProgram: (id: string) => request<Program>(`/api/v1/programs/${id}/`),

  listCohorts: () => request<Paginated<Cohort>>("/api/v1/cohorts/"),
  createCohort: (body: { name: string; capacity?: number; status?: string }) =>
    request<Cohort>("/api/v1/cohorts/", { method: "POST", body }),
  getCohort: (id: string) => request<Cohort>(`/api/v1/cohorts/${id}/`),
  updateCohort: (id: string, body: Partial<Cohort> & { name?: string; capacity?: number }) =>
    request<Cohort>(`/api/v1/cohorts/${id}/`, { method: "PATCH", body }),
  deleteCohort: (id: string) => request<void>(`/api/v1/cohorts/${id}/`, { method: "DELETE" }),
  openApplications: (id: string) =>
    request<Cohort>(`/api/v1/cohorts/${id}/open-applications/`, { method: "POST", body: {} }),
  closeApplications: (id: string) =>
    request<Cohort>(`/api/v1/cohorts/${id}/close-applications/`, { method: "POST", body: {} }),

  listClasses: (cohort?: string) =>
    request<Paginated<ClassItem>>(listPath("/api/v1/classes/", { cohort })),
  createClass: (body: { name: string; cohort: string; description?: string }) =>
    request<ClassItem>("/api/v1/classes/", { method: "POST", body }),
  getClass: (id: string) => request<ClassItem>(`/api/v1/classes/${id}/`),
  updateClass: (id: string, body: Partial<ClassItem> & { name?: string; description?: string }) =>
    request<ClassItem>(`/api/v1/classes/${id}/`, { method: "PATCH", body }),
  deleteClass: (id: string) => request<void>(`/api/v1/classes/${id}/`, { method: "DELETE" }),
  publishClass: (id: string) =>
    request<ClassItem>(`/api/v1/classes/${id}/publish/`, { method: "POST", body: {} }),
  listClassSubjects: (id: string) => request<ClassSubjectLink[]>(`/api/v1/classes/${id}/subjects/`),
  attachSubject: (classId: string, subjectId: string, mode = "linked") =>
    request<ClassSubjectLink>(`/api/v1/classes/${classId}/subjects/`, {
      method: "POST",
      body: { subject_id: subjectId, mode },
    }),

  listSubjects: () => request<Paginated<Subject>>("/api/v1/subjects/"),
  createSubject: (body: { title: string; level?: string; subtitle?: string }) =>
    request<Subject>("/api/v1/subjects/", { method: "POST", body }),
  getSubject: (id: string) => request<Subject>(`/api/v1/subjects/${id}/`),
  updateSubject: (id: string, body: Partial<Subject>) =>
    request<Subject>(`/api/v1/subjects/${id}/`, { method: "PATCH", body }),
  deleteSubject: (id: string) => request<void>(`/api/v1/subjects/${id}/`, { method: "DELETE" }),
  publishSubject: (id: string, force = false) =>
    request<Subject>(`/api/v1/subjects/${id}/publish/`, { method: "POST", body: { force } }),
  getSubjectChecklist: (id: string) => request<SubjectChecklist>(`/api/v1/subjects/${id}/checklist/`),
  getCurriculum: (id: string) => request<CurriculumTopic[]>(`/api/v1/subjects/${id}/curriculum/`),
  getIntendedLearners: (id: string) =>
    request<{ learn: string[]; requirements: string[]; audience: string[] }>(
      `/api/v1/subjects/${id}/intended-learners/`,
    ),
  putIntendedLearners: (
    id: string,
    body: { learn: string[]; requirements: string[]; audience: string[] },
  ) =>
    request<{ learn: string[]; requirements: string[]; audience: string[] }>(
      `/api/v1/subjects/${id}/intended-learners/`,
      { method: "PUT", body },
    ),
  putLanding: (id: string, body: Record<string, unknown>) =>
    request<Subject>(`/api/v1/subjects/${id}/landing/`, { method: "PUT", body }),
  getPricing: (id: string) => request<Record<string, unknown>>(`/api/v1/subjects/${id}/pricing/`),
  putPricing: (id: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/api/v1/subjects/${id}/pricing/`, { method: "PUT", body }),
  getMessages: (id: string) =>
    request<{ welcome_message: string; completion_message: string }>(
      `/api/v1/subjects/${id}/messages/`,
    ),
  putMessages: (id: string, body: { welcome_message: string; completion_message: string }) =>
    request<{ welcome_message: string; completion_message: string }>(
      `/api/v1/subjects/${id}/messages/`,
      { method: "PUT", body },
    ),
  getSubjectSettings: (id: string) => request<Record<string, unknown>>(`/api/v1/subjects/${id}/settings/`),
  putSubjectSettings: (id: string, settings: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/api/v1/subjects/${id}/settings/`, {
      method: "PUT",
      body: { settings },
    }),
  createPreviewToken: (id: string) =>
    request<{ token: string; expires_at: string; preview_path: string }>(
      `/api/v1/subjects/${id}/preview-token/`,
      { method: "POST", body: {} },
    ),
  listTopics: (subjectId: string) => request<Topic[]>(`/api/v1/subjects/${subjectId}/topics/`),
  createTopic: (subjectId: string, body: { title: string; objective_text?: string }) =>
    request<Topic>(`/api/v1/subjects/${subjectId}/topics/`, { method: "POST", body }),
  updateTopic: (id: string, body: Partial<Topic>) =>
    request<Topic>(`/api/v1/topics/${id}/`, { method: "PATCH", body }),
  deleteTopic: (id: string) => request<void>(`/api/v1/topics/${id}/`, { method: "DELETE" }),
  duplicateTopic: (id: string) =>
    request<Topic>(`/api/v1/topics/${id}/duplicate/`, { method: "POST", body: {} }),
  reorderTopics: (subjectId: string, ordered_ids: string[]) =>
    request<Topic[]>(`/api/v1/subjects/${subjectId}/topics/reorder/`, {
      method: "POST",
      body: { ordered_ids },
    }),
  listSubtopics: (topicId: string) => request<Subtopic[]>(`/api/v1/topics/${topicId}/subtopics/`),
  getSubtopic: (id: string) => request<Subtopic>(`/api/v1/subtopics/${id}/`),
  createSubtopic: (
    topicId: string,
    body: { title: string; kind?: string; min_time_s?: number },
  ) => request<Subtopic>(`/api/v1/topics/${topicId}/subtopics/`, { method: "POST", body }),
  updateSubtopic: (id: string, body: Partial<Subtopic>) =>
    request<Subtopic>(`/api/v1/subtopics/${id}/`, { method: "PATCH", body }),
  deleteSubtopic: (id: string) => request<void>(`/api/v1/subtopics/${id}/`, { method: "DELETE" }),
  duplicateSubtopic: (id: string) =>
    request<Subtopic>(`/api/v1/subtopics/${id}/duplicate/`, { method: "POST", body: {} }),
  reorderSubtopics: (topicId: string, ordered_ids: string[]) =>
    request<Subtopic[]>(`/api/v1/topics/${topicId}/subtopics/reorder/`, {
      method: "POST",
      body: { ordered_ids },
    }),
  setSubtopicContent: (
    id: string,
    body: {
      content_type: string;
      title?: string;
      body_json?: Record<string, unknown>;
      external_url?: string;
      upload_id?: string;
      mux_upload_id?: string;
      video_asset_id?: string;
      duration_s?: number;
      metadata?: Record<string, unknown>;
    },
  ) => request<SubtopicContent>(`/api/v1/subtopics/${id}/content/`, { method: "POST", body }),
  getSubtopicContent: (id: string) => request<SubtopicContent>(`/api/v1/subtopics/${id}/content/`),
  addSubtopicResource: (
    id: string,
    body: { kind: string; title: string; url?: string; upload_id?: string },
  ) => request<SubtopicResource>(`/api/v1/subtopics/${id}/resources/`, { method: "POST", body }),
  listSubtopicResources: (id: string) =>
    request<SubtopicResource[]>(`/api/v1/subtopics/${id}/resources/`),
  presignUpload: (body: {
    purpose: string;
    filename: string;
    mime_type?: string;
    size_bytes?: number;
    subtopic_id?: string;
  }) =>
    request<{
      upload_id: string;
      object_key: string;
      upload_url: string;
      method: string;
      headers?: Record<string, string>;
    }>("/api/v1/uploads/presign", { method: "POST", body }),
  completeUpload: async (uploadId: string) => {
    return request<{ id: string; status: string; filename: string }>(
      `/api/v1/uploads/${uploadId}/complete`,
      { method: "POST", body: {} },
    );
  },
  uploadFile: async (file: File, purpose: string, subtopicId?: string) => {
    const presign = await api.presignUpload({
      purpose,
      filename: file.name,
      mime_type: file.type || "application/octet-stream",
      size_bytes: file.size,
      subtopic_id: subtopicId,
    });
    const putHeaders: Record<string, string> = {
      ...(presign.headers ?? {}),
    };
    const putRes = await fetch(presign.upload_url, {
      method: presign.method || "PUT",
      headers: putHeaders,
      body: file,
    });
    if (!putRes.ok) {
      throw { message: `Storage upload failed (${putRes.status})` };
    }
    await api.completeUpload(presign.upload_id);
    return presign.upload_id;
  },
  createMuxUpload: (subtopicId: string, corsOrigin?: string) =>
    request<{
      upload_id: string;
      upload_url: string;
      video_asset_id: string;
      content_id: string;
      status: string;
    }>(`/api/v1/subtopics/${subtopicId}/mux-upload`, {
      method: "POST",
      body: { cors_origin: corsOrigin || (typeof window !== "undefined" ? window.location.origin : "") },
    }),
  uploadVideoToMux: async (subtopicId: string, file: File) => {
    const created = await api.createMuxUpload(subtopicId);
    const putRes = await fetch(created.upload_url, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": file.type || "video/mp4" },
    });
    if (!putRes.ok) {
      throw { message: `Mux upload failed (${putRes.status})` };
    }
    await api.setSubtopicContent(subtopicId, {
      content_type: "video",
      mux_upload_id: created.upload_id,
      video_asset_id: created.video_asset_id,
      title: file.name,
    });
    return created;
  },

  getGatewaySettings: () => request<GatewaySettings>("/api/v1/settings/payments/gateway"),
  updateGatewaySettings: (body: Record<string, unknown>) =>
    request<GatewaySettings>("/api/v1/settings/payments/gateway", { method: "PUT", body }),
  getApplicationFeeSettings: () =>
    request<ApplicationFeeSettings>("/api/v1/settings/payments/application-fees"),
  updateApplicationFeeSettings: (body: Record<string, unknown>) =>
    request<ApplicationFeeSettings>("/api/v1/settings/payments/application-fees", {
      method: "PUT",
      body,
    }),
  testPaymentWebhook: () =>
    request<{ ok: boolean; message: string }>("/api/v1/settings/payments/test-webhook", {
      method: "POST",
      body: {},
    }),

  listPublicCohorts: () =>
    request<Paginated<Cohort>>("/api/v1/public/cohorts/", { auth: false }),
  getPublicCohort: (slug: string) =>
    request<PublicCohort>(`/api/v1/public/cohorts/${slug}/`, { auth: false }),
  submitApplication: (
    slug: string,
    body: { full_name: string; email: string; phone?: string; data?: Record<string, unknown> },
  ) =>
    request<{ application_id: string; email: string; status: string; message: string }>(
      `/api/v1/public/applications/${slug}/`,
      { method: "POST", body, auth: false },
    ),
  resendOnboarding: (applicationId: string) =>
    request<{ detail: string }>(`/api/v1/public/applications/by-id/${applicationId}/resend-onboarding`, {
      method: "POST",
      body: {},
      auth: false,
    }),
  changeApplicationEmail: (applicationId: string, email: string) =>
    request<{ detail: string }>(`/api/v1/public/applications/by-id/${applicationId}/email`, {
      method: "PATCH",
      body: { email },
      auth: false,
    }),
  verifyOnboarding: (token: string, applicationId: string) =>
    request<{ valid: boolean; email: string; name: string }>("/api/v1/auth/onboarding/verify", {
      method: "POST",
      body: { token, application_id: applicationId },
      auth: false,
    }),
  setOnboardingPassword: (token: string, applicationId: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/onboarding/set-password", {
      method: "POST",
      body: { token, application_id: applicationId, password },
      auth: false,
    }),
  listPortalApplications: () => request<ApplicationItem[]>("/api/v1/portal/applications"),
  getPortalApplication: (id: string) => request<ApplicationItem>(`/api/v1/portal/applications/${id}`),
  payApplicationFee: (id: string, idempotencyKey: string) =>
    request<PayInitResponse>(`/api/v1/portal/applications/${id}/pay`, {
      method: "POST",
      body: {},
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  paymentStatus: (reference: string) =>
    request<{
      reference: string;
      status: string;
      amount_minor: number;
      currency: string;
      invoice_status: string;
      paid_at: string | null;
    }>(`/api/v1/payments/${reference}/status`),
  listAdminApplications: (query?: { status?: string; cohort?: string }) =>
    request<ApplicationItem[]>(listPath("/api/v1/applications", query)),
  getAdminApplication: (id: string) => request<ApplicationItem>(`/api/v1/applications/${id}`),
  admitApplication: (
    id: string,
    body: { class_ids: string[]; fee_handling?: string; notes?: string },
  ) => request<ApplicationItem>(`/api/v1/applications/${id}/admit`, { method: "POST", body }),
  bulkAdmit: (body: {
    application_ids: string[];
    class_ids: string[];
    fee_handling?: string;
    notes?: string;
  }) => request<{ results: { id: string; ok: boolean; status?: string; error?: string }[] }>(
    "/api/v1/applications/bulk-admit",
    { method: "POST", body },
  ),
  myLearning: () =>
    request<{
      continue: LearningSubjectCard | null;
      subjects: LearningSubjectCard[];
      classes: LearningClassGroup[];
    }>("/api/v1/me/learning"),
  getSubjectLanding: (slug: string) => request<SubjectLanding>(`/api/v1/learn/subjects/${slug}/landing`),
  getPlayerOutline: (subjectId: string) =>
    request<PlayerOutline>(`/api/v1/learn/subjects/${subjectId}/outline`),
  getSubtopicViewer: (subtopicId: string) =>
    request<SubtopicViewer>(`/api/v1/learn/subtopics/${subtopicId}/viewer`),
  heartbeat: (subtopicId: string, body: { delta_s?: number; position_s?: number }) =>
    request<{
      time_spent_s: number;
      status: string;
      can_complete: boolean;
      min_time_s: number;
    }>(`/api/v1/learn/subtopics/${subtopicId}/heartbeat`, { method: "POST", body }),
  completeSubtopic: (subtopicId: string) =>
    request<{ status: string; completed_at: string | null; time_spent_s: number }>(
      `/api/v1/learn/subtopics/${subtopicId}/complete`,
      { method: "POST", body: {} },
    ),
  putVideoProgress: (
    subtopicId: string,
    body: {
      position_s: number;
      duration_s?: number;
      rate?: number;
      segments?: number[][];
      device_id?: string;
      client_ts?: number;
    },
  ) =>
    request<{
      last_position_s: number;
      resume_position_s: number;
      furthest_position_s: number;
      watched_pct: number;
    }>(`/api/v1/learn/subtopics/${subtopicId}/video-progress`, { method: "PUT", body }),
  listQA: (subjectId: string, query?: { subtopic?: string; q?: string }) =>
    request<QAQuestion[]>(listPath(`/api/v1/learn/subjects/${subjectId}/qa`, query)),
  askQuestion: (subjectId: string, body: { title: string; body: string; subtopic_id?: string }) =>
    request<QAQuestion>(`/api/v1/learn/subjects/${subjectId}/qa`, { method: "POST", body }),
  answerQuestion: (questionId: string, body: string) =>
    request<{ id: string; body: string; is_instructor: boolean }>(
      `/api/v1/learn/questions/${questionId}/answers`,
      { method: "POST", body: { body } },
    ),
  listNotes: (subtopicId: string) => request<LearningNote[]>(`/api/v1/learn/subtopics/${subtopicId}/notes`),
  createNote: (subtopicId: string, body: { body: string; timestamp_s?: number | null }) =>
    request<LearningNote>(`/api/v1/learn/subtopics/${subtopicId}/notes`, { method: "POST", body }),
  updateNote: (noteId: string, body: { body: string; timestamp_s?: number | null }) =>
    request<LearningNote>(`/api/v1/learn/notes/${noteId}`, { method: "PATCH", body }),
  deleteNote: (noteId: string) =>
    request<void>(`/api/v1/learn/notes/${noteId}`, { method: "DELETE" }),

  listCertificateTemplates: () =>
    request<CertificateTemplate[]>("/api/v1/certificate-templates"),
  createCertificateTemplate: (body: {
    name: string;
    orientation?: string;
    page_size?: string;
    design?: Record<string, unknown>;
  }) => request<CertificateTemplate>("/api/v1/certificate-templates", { method: "POST", body }),
  getCertificateTemplate: (id: string) =>
    request<CertificateTemplate>(`/api/v1/certificate-templates/${id}`),
  updateCertificateTemplate: (
    id: string,
    body: { name?: string; design?: Record<string, unknown>; note?: string },
  ) => request<CertificateTemplate>(`/api/v1/certificate-templates/${id}`, { method: "PATCH", body }),
  deleteCertificateTemplate: (id: string) =>
    request<void>(`/api/v1/certificate-templates/${id}`, { method: "DELETE" }),
  updateAnnouncement: (id: string, body: { title?: string; body_json?: Record<string, unknown> }) =>
    request<{ id: string; title: string; scope_type: string }>(`/api/v1/announcements/${id}`, {
      method: "PATCH",
      body,
    }),
  deleteAnnouncement: (id: string) =>
    request<void>(`/api/v1/announcements/${id}`, { method: "DELETE" }),
  previewCertificateTemplate: (
    id: string,
    body: {
      design?: Record<string, unknown>;
      data_source?: "sample" | "enrollment";
      enrollment_id?: string;
      subject_id?: string;
    },
  ) =>
    request<{
      html: string;
      warnings: string[];
      data: Record<string, unknown>;
      preview_hash: string;
      blocking: string[];
    }>(`/api/v1/certificate-templates/${id}/preview`, { method: "POST", body }),
  publishCertificateTemplate: (id: string) =>
    request<{ template: CertificateTemplate; version: { id: string; version_no: number } }>(
      `/api/v1/certificate-templates/${id}/publish`,
      { method: "POST", body: {} },
    ),
  listCertificateRules: () => request<CertificateIssueRule[]>("/api/v1/certificate-issue-rules"),
  createCertificateRule: (body: {
    name?: string;
    template: string;
    class_ref?: string | null;
    subject?: string | null;
    criteria?: Record<string, unknown>;
    auto_issue?: boolean;
    valid_for_days?: number | null;
    is_active?: boolean;
  }) => request<CertificateIssueRule>("/api/v1/certificate-issue-rules", { method: "POST", body }),
  updateCertificateRule: (id: string, body: Record<string, unknown>) =>
    request<CertificateIssueRule>(`/api/v1/certificate-issue-rules/${id}`, {
      method: "PATCH",
      body,
    }),
  deleteCertificateRule: (id: string) =>
    request<void>(`/api/v1/certificate-issue-rules/${id}`, { method: "DELETE" }),
  listIssuedCertificates: () => request<IssuedCertificate[]>("/api/v1/certificates"),
  issueCertificate: (body: {
    enrollment_id: string;
    rule_id?: string;
    template_id?: string;
    subject_id?: string;
    force?: boolean;
  }) => request<IssuedCertificate>("/api/v1/certificates/issue", { method: "POST", body }),
  revokeCertificate: (id: string, reason?: string) =>
    request<IssuedCertificate>(`/api/v1/certificates/${id}/revoke`, {
      method: "POST",
      body: { reason: reason || "" },
    }),
  myCertificates: () => request<IssuedCertificate[]>("/api/v1/me/certificates"),
  verifyCertificate: (code: string) =>
    request<CertificateVerifyResult>(`/api/v1/public/certificates/verify/${code}`, { auth: false }),

  getSubtopicQuiz: (subtopicId: string) =>
    request<QuizDetail>(`/api/v1/subtopics/${subtopicId}/quiz/`),
  getQuiz: (quizId: string) => request<QuizDetail>(`/api/v1/quizzes/${quizId}`),
  startQuizAttempt: (quizId: string) =>
    request<QuizAttempt>(`/api/v1/quizzes/${quizId}/attempts`, { method: "POST", body: {} }),
  saveAttemptResponses: (
    attemptId: string,
    responses: { question_id: string; answer: Record<string, unknown> }[],
  ) =>
    request<QuizAttempt>(`/api/v1/attempts/${attemptId}/responses`, {
      method: "PUT",
      body: { responses },
    }),
  submitQuizAttempt: (attemptId: string) =>
    request<QuizAttempt & { released?: boolean }>(`/api/v1/attempts/${attemptId}/submit`, {
      method: "POST",
      body: {},
    }),
  reviewQuizAttempt: (attemptId: string) =>
    request<QuizAttemptReview>(`/api/v1/attempts/${attemptId}/review`),
  gradingQueue: (query?: { class_id?: string; assignment_id?: string }) =>
    request<{ results: GradingQueueItem[] }>(listPath("/api/v1/grading/queue", query)),
  gradeSubmission: (
    submissionId: string,
    body: {
      rubric_scores?: Record<string, unknown>;
      raw_score?: number;
      feedback_json?: Record<string, unknown>;
      penalty?: number;
    },
  ) =>
    request<SubmissionGradeResult>(`/api/v1/submissions/${submissionId}/grade`, {
      method: "PUT",
      body,
    }),
  releaseGrades: (submission_ids: string[]) =>
    request<{ results: { submission_id: string; ok: boolean; final_score?: number }[] }>(
      "/api/v1/grades/release",
      { method: "POST", body: { submission_ids } },
    ),
  classGradebook: (classId: string, subjectId?: string) =>
    request<GradebookPayload>(
      listPath(`/api/v1/classes/${classId}/gradebook`, { subject_id: subjectId }),
    ),
  myGrades: (classId?: string) =>
    request<{ results: ReleasedGrade[] }>(listPath("/api/v1/me/grades", { class_id: classId })),
};
