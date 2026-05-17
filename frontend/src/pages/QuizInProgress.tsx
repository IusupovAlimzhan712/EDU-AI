import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeft, Check, ChevronLeft, ChevronRight, Save, AlertTriangle,
  Sparkles, Loader2,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { api, QuizAttempt, QuizQuestionView, APIError } from '../lib/api';

interface QuizInProgressProps {
  onNavigate: (page: any, params?: any) => void;
  quizId: string | null;
  attemptId?: string | null;
}

export function QuizInProgress({
  onNavigate,
  quizId,
  attemptId: initialAttemptId,
}: QuizInProgressProps) {
  // ---------- Core state ----------
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [questions, setQuestions] = useState<QuizQuestionView[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);

  // ---------- Lifecycle flags ----------
  const [isLoadingAttempt, setIsLoadingAttempt] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ---------- Streaming state ----------
  //const [streamStatus, setStreamStatus] = useState
  const [streamStatus, setStreamStatus] = useState<'idle' | 'streaming' | 'done' | 'failed'>('idle');
  const [streamMessage, setStreamMessage] = useState<string | null>(null);
  const streamCtrlRef = useRef<AbortController | null>(null);
  const streamStartedRef = useRef<boolean>(false);

  // ---------- Saving + submitting ----------
  const [savingId, setSavingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);

  // ============ Load attempt + decide whether to stream ============

  useEffect(() => {
    if (!quizId) return;
    let cancelled = false;
    setIsLoadingAttempt(true);
    setError(null);

    const loader = initialAttemptId
      ? api.getAttempt(parseInt(initialAttemptId, 10))
      : api.startAttempt(parseInt(quizId, 10));

    loader
      .then((a) => {
        if (cancelled) return;

        if (a.status === 'submitted') {
          // Already submitted → bounce to results
          onNavigate('quiz-results', {
            quizId,
            attemptId: String(a.attemptId),
          });
          return;
        }

        setAttempt(a);
        const existing = a.questions ?? [];
        setQuestions(existing);

        // Resume on the first unanswered question if there are any answers yet
        const firstUnansweredIdx = existing.findIndex(
          (q) => q.selectedIndex === null,
        );
        setCurrentIdx(firstUnansweredIdx >= 0 ? firstUnansweredIdx : 0);

        // Decide whether we need to stream more questions
        if (a.generationStatus === 'ready' && existing.length >= a.targetQuestionCount) {
          setStreamStatus('done');
        } else if (a.generationStatus === 'failed') {
          setStreamStatus('failed');
          setStreamMessage(
            'Question generation failed previously. Try again from the Quizzes page.',
          );
        } else {
          // pending or partial — kick off (or resume) the stream
          startStream(a.attemptId);
        }
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof APIError ? err.message : 'Failed to load quiz.');
      })
      .finally(() => {
        if (!cancelled) setIsLoadingAttempt(false);
      });

    return () => {
          cancelled = true;
          streamCtrlRef.current?.abort();
          streamStartedRef.current = false;
        };

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizId, initialAttemptId]);

  // ============ SSE streaming ============
  
  const startStream = (aid: number) => {
      if (streamStartedRef.current) {
        // Strict-mode protection — effect fires twice in dev; we only want one stream
        return;
      }
      streamStartedRef.current = true;

      setStreamStatus('streaming');
      setStreamMessage(null);

      streamCtrlRef.current = api.streamAttemptQuestions(aid, {
  


      onQuestion: (q) => {
        setQuestions((prev) => {
          // Avoid duplicates if backend sends a question we already have
          if (prev.some((x) => x.attemptQuestionId === q.attemptQuestionId)) {
            return prev;
          }
          // Fresh AI-generated question: explicitly mark selectedIndex and
          // isCorrect as null. The backend doesn't send these fields for
          // fresh questions; without this, they default to `undefined`,
          // which makes the palette show the question as already answered
          // (because `undefined !== null` is true).
          return [...prev, { ...q, selectedIndex: null, isCorrect: null }];
        });
      },



      onDone: (info) => {
        setStreamStatus('done');
        setStreamMessage(
          info.total < info.target
            ? `Generated ${info.total}/${info.target} questions (some failed validation and were skipped).`
            : null,
        );
      },
      onError: (msg) => {
        setStreamStatus('failed');
        setStreamMessage(msg);
      },
    });
  };

  // ============ Answer handling ============

  const handleSelect = async (selected: number) => {
    const current = questions[currentIdx];
    if (!attempt || !current) return;

    const newValue = current.selectedIndex === selected ? null : selected;

    // Optimistic update
    const prevQuestions = questions;
    setQuestions(
      questions.map((q, i) =>
        i === currentIdx ? { ...q, selectedIndex: newValue } : q,
      ),
    );

    setSavingId(current.attemptQuestionId);
    try {
      await api.saveAnswer(attempt.attemptId, current.attemptQuestionId, newValue);
    } catch (err) {
      setQuestions(prevQuestions);
      setError(err instanceof APIError ? err.message : 'Failed to save answer.');
    } finally {
      setSavingId(null);
    }
  };

  // ============ Submit ============

  const handleSubmit = async () => {
    if (!attempt) return;
    setSubmitting(true);
    try {
      await api.submitAttempt(attempt.attemptId);
      onNavigate('quiz-results', {
        quizId,
        attemptId: String(attempt.attemptId),
      });
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Failed to submit quiz.');
      setSubmitting(false);
    }
  };

  // ============ Render ============

  const current = questions[currentIdx];
  const answeredCount = questions.filter((q) => q.selectedIndex !== null).length;
  const target = attempt?.targetQuestionCount ?? 0;
  const streamProgress = target > 0 ? Math.round((questions.length / target) * 100) : 0;
  const isStreaming = streamStatus === 'streaming';
  const hasAtLeastOne = questions.length > 0;
  const canSubmit =
    streamStatus !== 'streaming' && questions.length > 0;

  // ----- Loading the attempt itself -----
  if (isLoadingAttempt) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
        <div className="flex items-center gap-3 text-[#6B7280]">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading quiz…
        </div>
      </div>
    );
  }

  // ----- Hard error -----
  if (error || !attempt) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow-edu-sm p-8 max-w-md text-center">
          <AlertTriangle className="w-10 h-10 text-[#F59E0B] mx-auto mb-3" />
          <p className="font-bold text-[#111827] mb-2">
            {error ?? 'Could not load this quiz.'}
          </p>
          <Button onClick={() => onNavigate('quiz-selection')}>Back to Quizzes</Button>
        </div>
      </div>
    );
  }

  // ----- Generation failed and we have nothing to show -----
  if (streamStatus === 'failed' && !hasAtLeastOne) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow-edu-sm p-8 max-w-md text-center">
          <AlertTriangle className="w-10 h-10 text-[#DC2626] mx-auto mb-3" />
          <p className="font-bold text-[#111827] mb-2">Question generation failed</p>
          <p className="text-sm text-[#6B7280] mb-4">
            {streamMessage ?? 'The AI was unable to produce questions for this quiz.'}
          </p>
          <p className="text-xs text-[#9CA3AF] mb-4">
            Common cause: Ollama is not running, or the PDF for this chapter has
            no extracted text. Check the backend logs.
          </p>
          <Button onClick={() => onNavigate('quiz-selection')}>Back to Quizzes</Button>
        </div>
      </div>
    );
  }

  // ----- Waiting for the very first question to arrive -----
  if (isStreaming && !hasAtLeastOne) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center mb-4">
          <Sparkles className="w-7 h-7 text-white animate-pulse" />
        </div>
        <h2 className="text-xl font-bold text-[#111827] mb-2">
          Generating your quiz…
        </h2>
        <p className="text-[#6B7280] max-w-md mb-4">
          The AI is reading the KSSM textbook and writing
          {' '}{target}{' '} fresh MCQ questions. First question usually arrives in
          5-15 seconds, total time around {Math.ceil(target * 4)}-{target * 8}s.
        </p>
        <p className="text-xs text-[#9CA3AF]">
          On the very first quiz after starting the backend, this takes longer —
          the model is loading into RAM (cold start).
        </p>
        <Button
          variant="outline"
          onClick={() => {
            streamCtrlRef.current?.abort();
            onNavigate('quiz-selection');
          }}
          className="mt-6"
        >
          Cancel
        </Button>
      </div>
    );
  }

  // ----- Normal quiz runner -----
  return (
    <div className="min-h-screen bg-[#F9FAFB] flex flex-col">
      {/* Top bar */}
      <div className="bg-white border-b border-[#E5E7EB] px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => onNavigate('quiz-selection')}
          className="p-2 hover:bg-[#F3F4F6] rounded"
          title="Back (your progress is saved)"
        >
          <ArrowLeft className="w-5 h-5 text-[#6B7280]" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="font-bold text-[#111827] truncate">
            {attempt.quiz?.title}
          </h1>
          <p className="text-xs text-[#6B7280]">
            Answered {answeredCount} of {questions.length}
            {isStreaming && ` — generating ${questions.length}/${target}…`}
            {!isStreaming && questions.length < target && streamStatus === 'done' &&
              ` (${target - questions.length} skipped)`}
          </p>
        </div>
        <Button
          onClick={() => setShowSubmitConfirm(true)}
          disabled={!canSubmit || submitting}
          className="bg-[#059669] hover:bg-[#047857] text-white disabled:opacity-50"
          title={isStreaming ? 'Wait for generation to finish before submitting' : undefined}
        >
          <Check className="w-4 h-4 mr-2" />
          Submit
        </Button>
      </div>

      {/* Streaming progress bar */}
      {isStreaming && (
        <div className="bg-[#EFF6FF] border-b border-[#1E3A8A]/20 px-6 py-3 flex items-center gap-3">
          <Sparkles className="w-4 h-4 text-[#1E3A8A] animate-pulse" />
          <div className="flex-1">
            <p className="text-sm text-[#1E3A8A] font-medium">
              AI is generating more questions…
            </p>
            <Progress value={streamProgress} className="h-1 mt-1" />
          </div>
          <span className="text-sm text-[#1E3A8A] font-mono">
            {questions.length}/{target}
          </span>
        </div>
      )}

      <div className="flex-1 flex">
        {/* Palette */}
        <aside className="w-56 bg-white border-r border-[#E5E7EB] p-4 overflow-y-auto">
          <p className="text-xs font-semibold uppercase tracking-wide text-[#6B7280] mb-3">
            Questions
          </p>
          <div className="grid grid-cols-5 gap-2">
            {questions.map((q, i) => {
              const answered = q.selectedIndex !== null;
              const isCurrent = i === currentIdx;
              return (
                <button
                  key={q.attemptQuestionId}
                  onClick={() => setCurrentIdx(i)}
                  className={`w-9 h-9 rounded font-medium text-sm transition-colors ${
                    isCurrent
                      ? 'bg-[#1E3A8A] text-white'
                      : answered
                      ? 'bg-[#D1FAE5] text-[#065F46] hover:bg-[#A7F3D0]'
                      : 'bg-[#F3F4F6] text-[#6B7280] hover:bg-[#E5E7EB]'
                  }`}
                >
                  {i + 1}
                </button>
              );
            })}
            {/* Placeholder slots while generation is still streaming */}
            {isStreaming &&
              Array.from({ length: Math.max(0, target - questions.length) }).map((_, i) => (
                <div
                  key={`pending-${i}`}
                  className="w-9 h-9 rounded bg-[#F3F4F6] border-2 border-dashed border-[#D1D5DB] flex items-center justify-center"
                  title="Waiting for AI…"
                >
                  <Loader2 className="w-3 h-3 text-[#9CA3AF] animate-spin" />
                </div>
              ))}
          </div>

          <div className="mt-6 space-y-2 text-xs text-[#6B7280]">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#D1FAE5]"></span> Answered
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#F3F4F6]"></span> Not answered
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-[#1E3A8A]"></span> Current
            </div>
            {isStreaming && (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded border-2 border-dashed border-[#D1D5DB]"></span>
                Generating
              </div>
            )}
          </div>
        </aside>

        {/* Question detail */}
        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-xl shadow-edu-sm p-8 mb-6">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-semibold text-[#1E3A8A]">
                  Question {currentIdx + 1} of {questions.length}
                  {isStreaming && ` (of ${target} target)`}
                </span>
                {savingId === current?.attemptQuestionId && (
                  <span className="text-xs text-[#6B7280] flex items-center gap-1">
                    <Save className="w-3 h-3 animate-pulse" /> Saving…
                  </span>
                )}
              </div>

              {current ? (
                <>
                  <p className="text-lg text-[#111827] mb-6 whitespace-pre-wrap">
                    {current.stem}
                  </p>

                  <div className="space-y-3">
                    {current.options.map((opt, idx) => {
                      const selected = current.selectedIndex === idx;
                      return (
                        <button
                          key={idx}
                          onClick={() => handleSelect(idx)}
                          className={`w-full p-4 rounded-lg border-2 text-left transition-default ${
                            selected
                              ? 'border-[#1E3A8A] bg-[#EFF6FF]'
                              : 'border-[#E5E7EB] bg-white hover:border-[#9CA3AF]'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <span
                              className={`w-7 h-7 rounded-full border-2 flex items-center justify-center font-bold text-sm flex-shrink-0 ${
                                selected
                                  ? 'border-[#1E3A8A] bg-[#1E3A8A] text-white'
                                  : 'border-[#D1D5DB] text-[#6B7280]'
                              }`}
                            >
                              {String.fromCharCode(65 + idx)}
                            </span>
                            <span className="text-[#111827] pt-0.5">{opt}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </>
              ) : (
                <p className="text-[#6B7280] text-center py-8">
                  No question selected.
                </p>
              )}
            </div>

            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
                disabled={currentIdx === 0}
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Previous
              </Button>
              <Button
                onClick={() =>
                  setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))
                }
                disabled={currentIdx === questions.length - 1}
              >
                Next
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>

            {streamStatus === 'failed' && hasAtLeastOne && (
              <div className="mt-4 p-3 rounded-lg bg-[#FEE2E2] border border-[#DC2626]/20 text-sm text-[#991B1B]">
                {streamMessage ?? 'Some questions failed to generate.'} You can still
                submit with the {questions.length} questions you have.
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Submit confirmation */}
      {showSubmitConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-edu-xl p-6 max-w-md w-full">
            <h3 className="text-xl font-bold text-[#111827] mb-2">Submit quiz?</h3>
            <p className="text-[#6B7280] mb-4">
              You've answered <span className="font-semibold">{answeredCount}</span> of{' '}
              <span className="font-semibold">{questions.length}</span> questions.
              {answeredCount < questions.length && (
                <span className="block mt-2 text-[#F59E0B]">
                  Unanswered questions will be marked incorrect.
                </span>
              )}
            </p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setShowSubmitConfirm(false)}>
                Keep answering
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting}
                className="bg-[#059669] hover:bg-[#047857] text-white"
              >
                {submitting ? 'Submitting…' : 'Submit now'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}