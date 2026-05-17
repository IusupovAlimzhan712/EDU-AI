import { useEffect, useState } from 'react';
import {
  ClipboardList, Clock, Play, RotateCw, Trophy, Sparkles,
} from 'lucide-react';
import { AppSidebar } from '../components/AppSidebar';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useAuth } from '../context/AuthContext';
import { api, QuizSummary, APIError } from '../lib/api';

interface QuizSelectionProps {
  onNavigate: (page: any, params?: any) => void;
}

export function QuizSelection({ onNavigate }: QuizSelectionProps) {
  const { student } = useAuth();
  const [selectedForm, setSelectedForm] = useState<'4' | '5'>(
    student?.formLevel === 5 ? '5' : '4'
  );
  const [quizzes, setQuizzes] = useState<QuizSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    api
      .listQuizzes(parseInt(selectedForm, 10))
      .then((list) => {
        if (!cancelled) setQuizzes(list);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof APIError ? err.message : 'Failed to load quizzes.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedForm]);

  const megaQuiz = quizzes.find((q) => q.scope === 'form');
  const babQuizzes = quizzes
    .filter((q) => q.scope === 'bab')
    .sort((a, b) => (a.chapterId ?? 0) - (b.chapterId ?? 0));

  const handleStartOrResume = async (quiz: QuizSummary) => {
    setStartingId(quiz.quizId);
    try {
      const attempt = await api.startAttempt(quiz.quizId);
      // Whether resumed or fresh — both end up at the quiz runner.
      // The runner itself decides whether to stream questions or display
      // what was already generated.
      onNavigate('quiz-in-progress', {
        quizId: String(quiz.quizId),
        attemptId: String(attempt.attemptId),
      });
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Failed to start quiz.');
    } finally {
      setStartingId(null);
    }
  };

  // ---------- Card ----------
  const QuizCard = ({ quiz, isMega }: { quiz: QuizSummary; isMega?: boolean }) => {
    const inProgress = quiz.hasInProgressAttempt;
    const completed = (quiz.attemptCount ?? 0) > 0;
    const isStarting = startingId === quiz.quizId;

    return (
      <div
        className={`bg-white rounded-xl shadow-edu-sm p-5 ${
          isMega ? 'border-2 border-[#7C3AED]/30' : ''
        }`}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              {isMega && (
                <span className="px-2 py-0.5 text-xs font-bold text-[#7C3AED] bg-[#EDE9FE] rounded">
                  MEGA
                </span>
              )}
              <span className="px-2 py-0.5 text-xs text-[#1E3A8A] bg-[#DBEAFE] rounded flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> AI-generated
              </span>
              {inProgress && (
                <span className="px-2 py-0.5 text-xs text-[#F59E0B] bg-[#FEF3C7] rounded flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Resume
                </span>
              )}
            </div>
            <h3 className="font-bold text-[#111827] leading-tight">{quiz.title}</h3>
          </div>
        </div>

        <div className="flex items-center gap-4 text-sm text-[#6B7280] mb-4 flex-wrap">
          <span className="flex items-center gap-1">
            <ClipboardList className="w-4 h-4" />
            {quiz.defaultQuestionCount} questions per attempt
          </span>
          {completed && (
            <span className="text-[#059669]">
              {quiz.attemptCount} {quiz.attemptCount === 1 ? 'attempt' : 'attempts'}
            </span>
          )}
          {quiz.bestPercentage !== null && (
            <span className="flex items-center gap-1 text-[#F59E0B]">
              <Trophy className="w-4 h-4" />
              Best: {quiz.bestPercentage}%
            </span>
          )}
        </div>

        <Button
          onClick={() => handleStartOrResume(quiz)}
          disabled={isStarting}
          className={`w-full ${
            isMega
              ? 'bg-[#7C3AED] hover:bg-[#6D28D9]'
              : 'bg-[#1E3A8A] hover:bg-[#1E40AF]'
          } text-white`}
        >
          {isStarting ? (
            'Starting…'
          ) : inProgress ? (
            <>
              <RotateCw className="w-4 h-4 mr-2" />
              Resume Quiz
            </>
          ) : completed ? (
            <>
              <Sparkles className="w-4 h-4 mr-2" />
              Generate New Quiz
            </>
          ) : (
            <>
              <Play className="w-4 h-4 mr-2" />
              Generate Quiz
            </>
          )}
        </Button>

        {!inProgress && !completed && (
          <p className="text-xs text-[#6B7280] mt-2 text-center">
            Questions generated fresh by AI from the KSSM textbook.
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="quiz-selection" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827] mb-1">Quizzes</h1>
          <p className="text-[#6B7280]">
            Each click generates a fresh set of MCQ questions from the KSSM Sejarah
            textbook. Take it as many times as you like — every attempt is unique.
          </p>
        </div>

        <div className="p-8 max-w-6xl">
          <Tabs value={selectedForm} onValueChange={(v) => setSelectedForm(v as '4' | '5')}>
            <TabsList className="mb-6">
              <TabsTrigger value="4">Form 4</TabsTrigger>
              <TabsTrigger value="5">Form 5</TabsTrigger>
            </TabsList>

            {isLoading ? (
              <div className="text-center py-16 text-[#6B7280]">Loading quizzes…</div>
            ) : error ? (
              <div className="p-6 rounded-lg bg-[#FEE2E2] border border-[#DC2626]/20 text-[#991B1B]">
                {error}
              </div>
            ) : (
              <>
                {megaQuiz && (
                  <div className="mb-8">
                    <h2 className="text-sm font-semibold text-[#6B7280] uppercase tracking-wide mb-3">
                      Full-Form Mega Quiz
                    </h2>
                    <QuizCard quiz={megaQuiz} isMega />
                  </div>
                )}

                <h2 className="text-sm font-semibold text-[#6B7280] uppercase tracking-wide mb-3">
                  Per Chapter
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {babQuizzes.map((q) => (
                    <QuizCard key={q.quizId} quiz={q} />
                  ))}
                </div>
              </>
            )}
          </Tabs>
        </div>
      </div>
    </div>
  );
}