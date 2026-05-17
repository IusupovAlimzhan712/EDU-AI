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

// ── Client-side streaming normalizer ──────────────────────────────────────
// Applied to each token chunk BEFORE adding to the streaming buffer.
// The backend normalizes the final buffer too — this just prevents Indonesian
// words from briefly appearing during streaming.
const _STREAM_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\bkontribusinya\b/gi, 'sumbangannya'],
  [/\bkontribusi\b/gi,    'sumbangan'],
  [/\bpangeran\b/gi,      'putera'],
  [/\bTiongkok\b/g,       'China'],
  [/\btiongkok\b/g,       'china'],
  [/\bbahwa\b/gi,         'bahawa'],
  [/\bkarena\b/gi,        'kerana'],
  [/\bmemiliki\b/gi,      'mempunyai'],
  [/\bmenyebutkan\b/gi,   'menyatakan'],
  [/\bdikarenakan\b/gi,   'kerana'],
  [/\boknum\b/gi,         'individu'],
];

export function normalizeStreamChunk(chunk: string): string {
  return _STREAM_REPLACEMENTS.reduce((t, [re, r]) => t.replace(re, r), chunk);
}

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

// ============ Quiz module types ============

export interface QuizSummary {
  quizId: number;
  title: string;
  formLevel: number;
  chapterId: number | null;
  scope: 'bab' | 'form';
  source: 'seed' | 'ai';
  difficulty: string | null;
  defaultQuestionCount: number;          // ← was questionCount
  hasInProgressAttempt: boolean;
  inProgressAttemptId: number | null;
  attemptCount: number;
  bestScore: number | null;
  bestPercentage: number | null;
}

export interface QuizQuestionView {
  attemptQuestionId: number;
  orderIndex: number;
  stem: string;
  options: string[];
  points: number;
  // Mid-attempt: selectedIndex set after answering; isCorrect is null.
  // Post-submit: both set.
  selectedIndex: number | null;
  isCorrect: boolean | null;
  // Only present in review (post-submit):
  correctIndex?: number;
  explanation?: string | null;
}

export interface QuizAttempt {
  attemptId: number;
  quizId: number;
  status: 'in_progress' | 'submitted';
  generationStatus: 'pending' | 'generating' | 'ready' | 'failed';
  targetQuestionCount: number;
  startedAt: string;
  submittedAt: string | null;
  score: number | null;
  maxScore: number | null;
  correctCount: number | null;
  totalQuestions: number | null;
  percentage: number | null;
  quiz?: QuizSummary;
  questions?: QuizQuestionView[];
}

export interface AttemptAnswer {
  attemptId: number;
  attemptQuestionId: number;        // ← was questionId
  selectedIndex: number | null;
  isCorrect: boolean | null;
  answeredAt: string;
}

// ============ AI Tutor types ============

export interface ChatMessage {
  messageId: number;
  conversationId: number;
  role: 'user' | 'assistant';
  content: string;
  sourcePageStart: number | null;
  sourcePageEnd: number | null;
  validationStatus: 'ok' | 'warned' | 'na';
  validationWarning: string | null;
  createdAt: string;
}

export interface ChatConversation {
  conversationId: number;
  studentId: number;
  topicId: number;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
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

  // ============ Quiz module ============

  listQuizzes: (formLevel?: number) => {
    const qs = formLevel ? `?form_level=${formLevel}` : '';
    return request<QuizSummary[]>(`/quizzes${qs}`);
  },

  getQuiz: (quizId: number) =>
    request<QuizSummary & { questions: QuizQuestionView[] }>(
      `/quizzes/${quizId}`
    ),

  startAttempt: (quizId: number) =>
    request<QuizAttempt>(`/quizzes/${quizId}/attempts`, { method: 'POST' }),

  listMyAttempts: (quizId?: number) => {
    const qs = quizId ? `?quiz_id=${quizId}` : '';
    return request<QuizAttempt[]>(`/me/attempts${qs}`);
  },

  getAttempt: (attemptId: number) =>
    request<QuizAttempt>(`/me/attempts/${attemptId}`),

  saveAnswer: (
      attemptId: number,
      attemptQuestionId: number,                  // ← renamed from questionId
      selectedIndex: number | null,
    ) =>
      request<AttemptAnswer>(`/me/attempts/${attemptId}/answers`, {
        method: 'PATCH',
        body: { attemptQuestionId, selectedIndex },
      }),

  submitAttempt: (attemptId: number) =>
    request<QuizAttempt>(`/me/attempts/${attemptId}/submit`, {
      method: 'POST',
    }),

  // ============ AI Tutor ============

  getConversation: (topicId: number) =>
    request<ChatConversation>(`/me/topics/${topicId}/conversation`),

  clearConversation: (topicId: number) =>
    request<{ message: string }>(`/me/topics/${topicId}/conversation`, {
      method: 'DELETE',
    }),

  /**
   * Send a tutor message and stream the AI's reply via SSE.
   *
   * Events the callbacks handle:
   *   onToken : a chunk of the reply being streamed in real time
   *   onReset : retry happening; throw away whatever you've shown so far
   *   onFinal : the full validated response (definitive)
   *   onError : something went wrong
   *
   * Returns an AbortController to cancel the stream.
   */
  sendTutorMessage: (
    topicId: number,
    body: { question: string; currentPage: number },
    callbacks: {
      onToken: (chunk: string) => void;
      onReset: () => void;
      onFinal: (final: {
        content: string;
        validationStatus: 'ok' | 'warned';
        validationWarning: string | null;
        sourcePageStart: number | null;
        sourcePageEnd: number | null;
      }) => void;
      onError: (message: string) => void;
    },
  ): AbortController => {
    const controller = new AbortController();
    const token = tokenStore.getAccess();

    (async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/me/topics/${topicId}/messages`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify(body),
            signal: controller.signal,
          },
        );
        if (!res.ok) {
          callbacks.onError(`Tutor request failed (${res.status})`);
          return;
        }
        if (!res.body) {
          callbacks.onError('Streaming not supported by this browser.');
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const events = buffer.split('\n\n');
          buffer = events.pop() || '';

          for (const chunk of events) {
            const lines = chunk.split('\n');
            let eventName = 'message';
            let dataLine = '';
            for (const line of lines) {
              if (line.startsWith('event: ')) eventName = line.slice(7).trim();
              else if (line.startsWith('data: ')) dataLine = line.slice(6);
            }
            if (!dataLine) continue;

            let payload: any;
            try { payload = JSON.parse(dataLine); } catch { continue; }

            if (eventName === 'token' && payload?.chunk) {
              callbacks.onToken(normalizeStreamChunk(payload.chunk));
            } else if (eventName === 'reset') {
              callbacks.onReset();
            } else if (eventName === 'final') {
              callbacks.onFinal({
                content: payload.content ?? '',
                validationStatus: payload.validation_status ?? 'ok',
                validationWarning: payload.validation_warning ?? null,
                sourcePageStart: payload.source_page_start ?? null,
                sourcePageEnd: payload.source_page_end ?? null,
              });
            } else if (eventName === 'error') {
              callbacks.onError(payload.message ?? 'AI error.');
            }
          }
        }
      } catch (err: any) {
        if (err?.name !== 'AbortError') {
          callbacks.onError(err?.message ?? 'Stream error.');
        }
      }
    })();

    return controller;
  },

  /**
   * Free-form general tutor — searches ALL babs, no topic required.
   * History is passed as an array of recent {role, content} pairs.
   */
  sendGeneralTutorMessage: (
    body: {
      question: string;
      history: Array<{ role: 'user' | 'assistant'; content: string }>;
    },
    callbacks: {
      onToken: (chunk: string) => void;
      onReset: () => void;
      onFinal: (final: {
        content: string;
        validationStatus: 'ok' | 'warned';
        validationWarning: string | null;
        sourcePageStart: number | null;
        sourcePageEnd: number | null;
      }) => void;
      onError: (message: string) => void;
    },
  ): AbortController => {
    const controller = new AbortController();
    const token = tokenStore.getAccess();

    (async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/me/tutor/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(body),
          signal: controller.signal,
        });
        if (!res.ok) { callbacks.onError(`Tutor request failed (${res.status})`); return; }
        if (!res.body) { callbacks.onError('Streaming not supported.'); return; }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop() || '';
          for (const chunk of events) {
            const lines = chunk.split('\n');
            let eventName = 'message';
            let dataLine = '';
            for (const line of lines) {
              if (line.startsWith('event: ')) eventName = line.slice(7).trim();
              else if (line.startsWith('data: ')) dataLine = line.slice(6);
            }
            if (!dataLine) continue;
            let payload: any;
            try { payload = JSON.parse(dataLine); } catch { continue; }
            if (eventName === 'token' && payload?.chunk) callbacks.onToken(normalizeStreamChunk(payload.chunk));
            else if (eventName === 'reset') callbacks.onReset();
            else if (eventName === 'final') callbacks.onFinal({
              content: payload.content ?? '',
              validationStatus: payload.validation_status ?? 'ok',
              validationWarning: payload.validation_warning ?? null,
              sourcePageStart: payload.source_page_start ?? null,
              sourcePageEnd: payload.source_page_end ?? null,
            });
            else if (eventName === 'error') callbacks.onError(payload.message ?? 'AI error.');
          }
        }
      } catch (err: any) {
        if (err?.name !== 'AbortError') callbacks.onError(err?.message ?? 'Stream error.');
      }
    })();

    return controller;
  },

  /**
   * Stream AI question generation via Server-Sent Events.
   *
   * The browser's built-in EventSource doesn't support custom headers
   * (including Authorization), so we use fetch + ReadableStream and
   * parse the SSE protocol manually.
   *
   * Callbacks:
   *   onQuestion: called for every new question as it arrives
   *   onDone:     called when generation completes
   *   onError:    called if generation fails
   *
   * Returns an AbortController so callers can cancel mid-stream.
   */
  streamAttemptQuestions: (
    attemptId: number,
    callbacks: {
      onQuestion: (q: QuizQuestionView) => void;
      onDone: (info: { total: number; target: number }) => void;
      onError: (message: string) => void;
    },
  ): AbortController => {
    const controller = new AbortController();
    const token = tokenStore.getAccess();

    (async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/me/attempts/${attemptId}/stream`,
          {
            method: 'GET',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            signal: controller.signal,
          },
        );

        if (!res.ok) {
          callbacks.onError(`Stream failed (${res.status})`);
          return;
        }
        if (!res.body) {
          callbacks.onError('No response body — streaming unsupported by this browser.');
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // SSE events are separated by a blank line ("\n\n")
          const events = buffer.split('\n\n');
          buffer = events.pop() || ''; // last chunk may be incomplete

          for (const chunk of events) {
            const lines = chunk.split('\n');
            let eventName = 'message';
            let dataLine = '';
            for (const line of lines) {
              if (line.startsWith('event: ')) eventName = line.slice(7).trim();
              else if (line.startsWith('data: ')) dataLine = line.slice(6);
            }
            if (!dataLine) continue;

            let payload: any;
            try {
              payload = JSON.parse(dataLine);
            } catch {
              continue;
            }

            if (eventName === 'question' && payload?.question) {
              callbacks.onQuestion(payload.question);
            } else if (eventName === 'done') {
              callbacks.onDone({
                total: payload.total ?? 0,
                target: payload.target ?? 0,
              });
            } else if (eventName === 'error') {
              callbacks.onError(payload.message ?? 'Generation failed.');
            }
          }
        }
      } catch (err: any) {
        if (err?.name !== 'AbortError') {
          callbacks.onError(err?.message ?? 'Stream error.');
        }
      }
    })();

    return controller;
  },

  // ----- Health -----
  health: () =>
    request<{ status: string }>('/health', { auth: false }),
};
