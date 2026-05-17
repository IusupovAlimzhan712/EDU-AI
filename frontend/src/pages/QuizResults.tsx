import { useEffect, useState } from 'react';
import {
  Trophy, CheckCircle2, XCircle, RotateCw, Home, ChevronDown, ChevronUp,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { api, QuizAttempt, APIError } from '../lib/api';

interface QuizResultsProps {
  onNavigate: (page: any, params?: any) => void;
  quizId: string | null;
  attemptId?: string | null;
}

export function QuizResults({ onNavigate, quizId, attemptId }: QuizResultsProps) {
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    if (!attemptId) return;
    let cancelled = false;
    setIsLoading(true);
    api
      .getAttempt(parseInt(attemptId, 10))
      .then((a) => !cancelled && setAttempt(a))
      .catch((err) =>
        !cancelled && setError(err instanceof APIError ? err.message : 'Failed to load results.')
      )
      .finally(() => !cancelled && setIsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [attemptId]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center">
        <p className="text-[#6B7280]">Loading results…</p>
      </div>
    );
  }

  if (error || !attempt) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex items-center justify-center p-8">
        <div className="bg-white rounded-xl shadow-edu-sm p-8 max-w-md text-center">
          <p className="font-bold text-[#111827] mb-2">
            {error ?? 'Attempt not found.'}
          </p>
          <Button onClick={() => onNavigate('quiz-selection')}>Back to Quizzes</Button>
        </div>
      </div>
    );
  }

  const pct = attempt.percentage ?? 0;
  const verdict =
    pct >= 80 ? { label: 'Excellent!', color: '#059669', bg: '#D1FAE5' }
    : pct >= 60 ? { label: 'Good effort', color: '#1E3A8A', bg: '#DBEAFE' }
    : pct >= 40 ? { label: 'Keep practising', color: '#F59E0B', bg: '#FEF3C7' }
    : { label: 'Review and try again', color: '#DC2626', bg: '#FEE2E2' };

  const questions = attempt.questions ?? [];

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      {/* Header */}
      <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
        <h1 className="text-2xl font-bold text-[#111827]">
          {attempt.quiz?.title ?? 'Quiz Results'}
        </h1>
        <p className="text-[#6B7280]">
          Submitted {attempt.submittedAt ? new Date(attempt.submittedAt).toLocaleString() : ''}
        </p>
      </div>

      <div className="p-8 max-w-4xl mx-auto">
        {/* Score panel */}
        <div className="bg-white rounded-xl shadow-edu-sm p-8 mb-6">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div
              className="w-32 h-32 rounded-full flex flex-col items-center justify-center flex-shrink-0"
              style={{ backgroundColor: verdict.bg }}
            >
              <Trophy className="w-8 h-8 mb-1" style={{ color: verdict.color }} />
              <span className="text-2xl font-bold" style={{ color: verdict.color }}>
                {pct}%
              </span>
            </div>
            <div className="flex-1 text-center md:text-left">
              <p className="text-xl font-bold mb-1" style={{ color: verdict.color }}>
                {verdict.label}
              </p>
              <p className="text-[#111827] text-lg mb-1">
                You scored <span className="font-bold">{attempt.score}</span> out of{' '}
                <span className="font-bold">{attempt.maxScore}</span>
              </p>
              <p className="text-sm text-[#6B7280]">
                {attempt.correctCount} of {attempt.totalQuestions} correct
              </p>
              <Progress value={pct} className="mt-4 h-2" />
            </div>
          </div>

          <div className="flex gap-3 mt-6 flex-wrap">
            <Button
              onClick={() =>
                onNavigate('quiz-in-progress', { quizId, attemptId: null })
              }
              className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              <RotateCw className="w-4 h-4 mr-2" />
              Try again
            </Button>
            <Button variant="outline" onClick={() => onNavigate('quiz-selection')}>
              All quizzes
            </Button>
            <Button variant="outline" onClick={() => onNavigate('dashboard')}>
              <Home className="w-4 h-4 mr-2" />
              Dashboard
            </Button>
          </div>
        </div>

        {/* Per-question review */}
        <h2 className="text-lg font-bold text-[#111827] mb-4">Question Review</h2>
        <div className="space-y-3">
          {questions.map((q, i) => {
            const isCorrect = q.isCorrect === true;
            const isUnanswered = q.selectedIndex === null;
            const expanded = expandedId === q.attemptQuestionId;
            return (
              <div
                key={q.attemptQuestionId}
                className="bg-white rounded-xl shadow-edu-sm overflow-hidden"
              >
                <button
                  onClick={() => setExpandedId(expanded ? null : q.attemptQuestionId)}
                  className="w-full p-5 flex items-start gap-4 text-left hover:bg-[#F9FAFB]"
                >
                  <div className="flex-shrink-0 mt-0.5">
                    {isUnanswered ? (
                      <XCircle className="w-6 h-6 text-[#9CA3AF]" />
                    ) : isCorrect ? (
                      <CheckCircle2 className="w-6 h-6 text-[#059669]" />
                    ) : (
                      <XCircle className="w-6 h-6 text-[#DC2626]" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[#6B7280] mb-1">Question {i + 1}</p>
                    <p className="font-medium text-[#111827] line-clamp-2">{q.stem}</p>
                    {isUnanswered && (
                      <p className="text-xs text-[#9CA3AF] mt-1 italic">Not answered</p>
                    )}
                  </div>
                  {expanded ? (
                    <ChevronUp className="w-5 h-5 text-[#6B7280] flex-shrink-0" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-[#6B7280] flex-shrink-0" />
                  )}
                </button>

                {expanded && (
                  <div className="px-5 pb-5 pt-0 border-t border-[#F3F4F6]">
                    <div className="space-y-2 mt-4">
                      {q.options.map((opt, idx) => {
                        const isSelected = q.selectedIndex === idx;
                        const isAnswer = q.correctIndex === idx;
                        let cls = 'border-[#E5E7EB] bg-white';
                        if (isAnswer) cls = 'border-[#059669] bg-[#D1FAE5]';
                        else if (isSelected) cls = 'border-[#DC2626] bg-[#FEE2E2]';
                        return (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg border-2 flex items-center gap-3 ${cls}`}
                          >
                            <span className="font-bold text-sm w-6">
                              {String.fromCharCode(65 + idx)}
                            </span>
                            <span className="flex-1 text-sm text-[#111827]">{opt}</span>
                            {isAnswer && (
                              <span className="text-xs font-semibold text-[#059669]">
                                Correct
                              </span>
                            )}
                            {isSelected && !isAnswer && (
                              <span className="text-xs font-semibold text-[#DC2626]">
                                Your answer
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {q.explanation && (
                      <div className="mt-4 p-3 rounded-lg bg-[#EFF6FF] border border-[#1E3A8A]/20">
                        <p className="text-xs font-semibold text-[#1E3A8A] mb-1">
                          Explanation
                        </p>
                        <p className="text-sm text-[#111827]">{q.explanation}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}