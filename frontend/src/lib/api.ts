/**
 * Tiny fetch-based API client for the EduAI backend.
 *
 * Design notes
 * ------------
 * - We deliberately avoid axios — the standard `fetch` API is sufficient
 *   and adds zero bundle weight.
 * - Tokens are kept in `localStorage` under `eduai_access_token` and
 *   `eduai_refresh_token`. Any request returning 401 triggers an
 *   automatic refresh attempt, then a single retry.
 * - All endpoints below correspond to the routes in
 *   backend/app/routes/*.py — keep the two files in sync.
 */

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:5000/api';

const ACCESS_KEY = 'eduai_access_token';
const REFRESH_KEY = 'eduai_refresh_token';

// ---------- Token storage ----------

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh?: string) => {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ---------- Errors ----------

export class APIError extends Error {
  status: number;
  data: any;
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

// ---------- Core fetch wrapper ----------

interface RequestOptions {
  method?: string;
  body?: any;
  auth?: boolean; // include Authorization header (default: true)
  isRefresh?: boolean; // if true, use the refresh token instead of access
}

async function request<T = any>(path: string, opts: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    body,
    auth = true,
    isRefresh = false,
  } = opts;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (auth) {
    const token = isRefresh ? tokenStore.getRefresh() : tokenStore.getAccess();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Try to parse JSON either way so error responses' details flow through.
  let data: any = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    // ----- Auto-refresh on 401 (once) -----
    if (
      res.status === 401 &&
      auth &&
      !isRefresh &&
      tokenStore.getRefresh() &&
      !path.startsWith('/auth/login') &&
      !path.startsWith('/auth/register')
    ) {
      const refreshed = await tryRefresh();
      if (refreshed) {
        return request<T>(path, { ...opts, isRefresh: false });
      }
      // Refresh failed → log the user out
      tokenStore.clear();
    }
    const msg = (data && data.message) || `Request failed (${res.status})`;
    throw new APIError(msg, res.status, data);
  }

  return data as T;
}

async function tryRefresh(): Promise<boolean> {
  try {
    const data = await request<{ accessToken: string }>('/auth/refresh', {
      method: 'POST',
      auth: true,
      isRefresh: true,
    });
    if (data?.accessToken) {
      tokenStore.set(data.accessToken);
      return true;
    }
  } catch {
    /* swallow */
  }
  return false;
}

// ---------- Domain types ----------

export interface Student {
  studentId: number;
  email: string;
  fullName: string;
  formLevel: number;
  registrationDate: string;
}

export interface AuthResponse {
  message: string;
  student: Student;
  accessToken: string;
  refreshToken: string;
}

export interface Chapter {
  formLevel: number;
  chapterId: number;
  chapterName: string;
}

export interface TopicSummary {
  topicId: number;
  formLevel: number;
  chapterId: number;
  topicName: string;
  chapterName: string;
  estimatedDurationMinutes: number | null;
  hasPdf: boolean;
  totalPages: number;
  isCompleted: boolean;
  isBookmarked: boolean;
}

export interface TopicDetail extends TopicSummary {
  pdfPath: string | null;
}

export interface TopicPage {
  topicPageId: number;
  topicId: number;
  pageNumber: number;
  textContent: string;
  wordCount: number;
}


export interface ProgressOverview {
  progressId: number;
  studentId: number;
  totalTopics: number;
  completedTopicsCount: number;
  bookmarkedTopicsCount: number;
  completionRate: number;
  lastUpdated: string;
  byChapter: Array<{
    formLevel: number;
    chapterId: number;
    chapterName: string;
    totalTopics: number;
    completedTopics: number;
  }>;
}

// ---------- Public API ----------

export const api = {
  // ----- Auth -----
  register: (payload: {
    email: string;
    password: string;
    fullName: string;
    formLevel: number;
  }) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: payload,
      auth: false,
    }),

  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: payload,
      auth: false,
    }),

  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),

  forgotPassword: (email: string) =>
    request<{ message: string; devResetToken?: string }>(
      '/auth/forgot-password',
      { method: 'POST', body: { email }, auth: false }
    ),

  resetPassword: (token: string, newPassword: string) =>
    request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: { token, newPassword },
      auth: false,
    }),

  // ----- Profile / me -----
  getMe: () => request<Student>('/me'),

  updateMe: (payload: { fullName?: string; formLevel?: number }) =>
    request<{ message: string; student: Student }>('/me', {
      method: 'PATCH',
      body: payload,
    }),

  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ message: string }>('/me/change-password', {
      method: 'POST',
      body: { currentPassword, newPassword },
    }),

  deleteMe: () => request<{ message: string }>('/me', { method: 'DELETE' }),

  // ----- Chapters / Topics -----
  listChapters: (formLevel?: number) => {
    const qs = formLevel ? `?form_level=${formLevel}` : '';
    return request<Chapter[]>(`/chapters${qs}`);
  },

  listTopics: (params: {
    formLevel?: number;
    chapterId?: number;
    search?: string;
  } = {}) => {
    const qs = new URLSearchParams();
    if (params.formLevel) qs.set('form_level', String(params.formLevel));
    if (params.chapterId) qs.set('chapter_id', String(params.chapterId));
    if (params.search) qs.set('search', params.search);
    const suffix = qs.toString();
    return request<TopicSummary[]>(`/topics${suffix ? '?' + suffix : ''}`);
  },


  // PDF: build URL for react-pdf. We can't put the JWT in <Document file=...>
  // easily, so we expose both: a URL builder, and a fetcher that returns a Blob.
  getTopicPdfBlobUrl: async (topicId: number): Promise<string> => {
    const token = tokenStore.getAccess();
    const res = await fetch(`${API_BASE_URL}/topics/${topicId}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new APIError(`PDF fetch failed (${res.status})`, res.status);
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  getTopicPage: (topicId: number, pageNumber: number) =>
    request<TopicPage>(`/topics/${topicId}/pages/${pageNumber}`),

  getTopic: (topicId: number) =>
    request<TopicDetail>(`/topics/${topicId}`),

  bookmark: (topicId: number) =>
    request<{ message: string }>(`/topics/${topicId}/bookmark`, { method: 'POST' }),

  unbookmark: (topicId: number) =>
    request<{ message: string }>(`/topics/${topicId}/bookmark`, { method: 'DELETE' }),

  markComplete: (topicId: number) =>
    request<{ message: string }>(`/topics/${topicId}/complete`, { method: 'POST' }),

  unmarkComplete: (topicId: number) =>
    request<{ message: string }>(`/topics/${topicId}/complete`, { method: 'DELETE' }),

  // ----- Progress / bookmarks -----
  getProgress: () => request<ProgressOverview>('/me/progress'),

  getBookmarks: () => request<TopicSummary[]>('/me/bookmarks'),

  // ----- Health -----
  health: () =>
    request<{ status: string }>('/health', { auth: false }),
};
