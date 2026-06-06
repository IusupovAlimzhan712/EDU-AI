import { useEffect, useMemo, useState } from 'react';
import { AppSidebar } from '../components/AppSidebar';
import { CircularProgress } from '../components/CircularProgress';
import { Button } from '../components/ui/button';
import { TrendingUp, Award } from 'lucide-react';
import { api, ProgressOverview, QuizAttempt, EssayAttempt } from '../lib/api';

interface MyProgressProps {
  onNavigate: (page: any, params?: any) => void;
}

function AchievementCard({ achievement }: { achievement: Achievement }) {
  return (
    <div
      className={`border rounded-lg p-4 text-center transition-default ${
        achievement.earned ? 'border-[#059669] bg-[#ECFDF5]' : 'border-[#E5E7EB] opacity-50'
      }`}
    >
      <div className="text-4xl mb-2">{achievement.earned ? achievement.icon : '🔒'}</div>
      <h3 className="font-medium text-[#111827] mb-1">{achievement.title}</h3>
      {achievement.description && (
        <p className="text-xs text-[#9CA3AF] mb-1">{achievement.description}</p>
      )}
      <p className="text-xs text-[#6B7280]">{achievement.earned ? 'Earned' : 'Locked'}</p>
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-MY', {
    day: 'numeric',
    month: 'short',
  });
}

function computeStreakDays(attempts: QuizAttempt[]): number {
  const submittedDays = new Set(
    attempts
      .filter((a) => a.status === 'submitted' && a.submittedAt)
      .map((a) => new Date(a.submittedAt!).toDateString()),
  );
  let streak = 0;
  const today = new Date();
  for (let i = 0; i < 30; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    if (submittedDays.has(d.toDateString())) {
      streak++;
    } else if (i > 0) {
      break;
    }
  }
  return streak;
}

interface Achievement {
  title: string;
  description?: string;
  icon: string;
  earned: boolean;
  group: 'quiz' | 'essay';
}

function deriveAchievements(
  progress: ProgressOverview,
  attempts: QuizAttempt[],
  essayAttempts: EssayAttempt[],
): Achievement[] {
  const submitted = attempts.filter((a) => a.status === 'submitted');
  const completedAChapter = progress.byChapter.some(
    (c) => c.totalTopics > 0 && c.completedTopics === c.totalTopics,
  );
  const avgPct = progress.quizAverage ?? 0;

  const quizAchievements: Achievement[] = [
    { title: 'First Quiz Completed', icon: '🎯', earned: submitted.length >= 1, group: 'quiz' },
    { title: '5 Quizzes Done', icon: '🏆', earned: submitted.length >= 5, group: 'quiz' },
    { title: '100% Chapter Completion', icon: '⭐', earned: completedAChapter, group: 'quiz' },
    { title: 'Quiz Average ≥ 80%', icon: '🔥', earned: submitted.length > 0 && avgPct >= 80, group: 'quiz' },
  ];

  // Best score per unique question (mirrors backend achievement_service.py)
  const bestPct = new Map<number, number>();
  for (const ea of essayAttempts) {
    if (ea.gradingStatus !== 'done' || ea.score == null || !ea.maxScore || ea.maxScore <= 0) continue;
    const pct = (ea.score / ea.maxScore) * 100;
    if (pct > (bestPct.get(ea.questionId) ?? -1)) bestPct.set(ea.questionId, pct);
  }
  const completed = bestPct.size;
  const highScore = [...bestPct.values()].filter((p) => p >= 90).length;

  const essayAchievements: Achievement[] = [
    { title: 'Essay Beginner',   description: 'Complete 1 essay',         icon: '✏️', earned: completed >= 1,   group: 'essay' },
    { title: 'Essay Writer',     description: 'Complete 10 essays',        icon: '📝', earned: completed >= 10,  group: 'essay' },
    { title: 'Essay Expert',     description: 'Complete 25 essays',        icon: '📚', earned: completed >= 25,  group: 'essay' },
    { title: 'Essay Excellence', description: 'Score ≥ 90% on 5 essays',  icon: '⭐', earned: highScore >= 5,   group: 'essay' },
    { title: 'Essay Master',     description: 'Score ≥ 90% on 10 essays', icon: '🏆', earned: highScore >= 10,  group: 'essay' },
    { title: 'SPM Essay Elite',  description: 'Score ≥ 90% on 20 essays', icon: '👑', earned: highScore >= 20,  group: 'essay' },
  ];

  return [...quizAchievements, ...essayAchievements];
}

function chapterWeaknessScore(c: {
  totalTopics: number;
  completedTopics: number;
  quizAverage: number | null;
  essayAverage?: number | null;
}): number {
  const completionGap = c.totalTopics > 0 ? 1 - c.completedTopics / c.totalTopics : 1;
  const hasQuiz = c.quizAverage != null;
  const hasEssay = c.essayAverage != null;
  if (hasQuiz && hasEssay) {
    return 0.40 * (1 - (c.quizAverage as number) / 100)
         + 0.25 * (1 - (c.essayAverage as number) / 100)
         + 0.35 * completionGap;
  }
  if (hasQuiz) {
    return 0.55 * (1 - (c.quizAverage as number) / 100) + 0.45 * completionGap;
  }
  if (hasEssay) {
    return 0.45 * (1 - (c.essayAverage as number) / 100) + 0.55 * completionGap;
  }
  return completionGap;
}

export function MyProgress({ onNavigate }: MyProgressProps) {
  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [attempts, setAttempts] = useState<QuizAttempt[]>([]);
  const [essayAttempts, setEssayAttempts] = useState<EssayAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getProgress(), api.listMyAttempts(), api.listMyEssayAttempts()])
      .then(([p, a, ea]) => {
        setProgress(p);
        setAttempts(a);
        setEssayAttempts(ea);
      })
      .catch(() => setLoadError('Failed to load progress data. Please refresh the page.'))
      .finally(() => setLoading(false));
  }, []);

  const submitted = attempts.filter((a) => a.status === 'submitted');
  const streakDays = computeStreakDays(attempts);
  const achievements = useMemo(
    () => (progress ? deriveAchievements(progress, attempts, essayAttempts) : []),
    [progress, attempts, essayAttempts],
  );

  // Last 10 submitted attempts for trend chart (chronological order)
  // attempts arrive newest-first; reverse → oldest first; slice(0,10) → 10 oldest
  // of the most recent set; reverse again → chronological (oldest→newest for chart)
  const recentAttempts = [...submitted]
    .slice(0, 10)   // 10 most recent (newest first)
    .reverse()      // flip to chronological for left-to-right display
    .map((a) => ({
      label: a.quizTitle ?? (a.submittedAt ? formatDate(a.submittedAt) : '—'),
      date: a.submittedAt ? formatDate(a.submittedAt) : '—',
      score:
        a.score != null && a.maxScore && a.maxScore > 0
          ? Math.round((a.score / a.maxScore) * 100)
          : null,
      attemptId: a.attemptId,
      quizId: a.quizId,
    }));

  // Focus areas: blend topic completion, quiz performance, and essay performance.
  const focusChapters = useMemo(
    () =>
      (progress?.byChapter ?? [])
        .filter((c) =>
          c.totalTopics > 0 && (
            c.completedTopics / c.totalTopics < 0.5 ||
            (c.quizAverage != null && c.quizAverage < 70) ||
            (c.essayAverage != null && c.essayAverage < 70)
          )
        )
        .sort((a, b) => chapterWeaknessScore(b) - chapterWeaknessScore(a))
        .slice(0, 3),
    [progress],
  );

  // Streak heatmap: last 30 days, mark days with quiz activity
  const submittedDaySet = new Set(
    submitted
      .filter((a) => a.submittedAt)
      .map((a) => new Date(a.submittedAt!).toDateString()),
  );
  const heatmapDays = Array.from({ length: 30 }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return { date: d.toDateString(), active: submittedDaySet.has(d.toDateString()) };
  });

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="progress" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827] mb-1">My Progress</h1>
          <p className="text-[#6B7280]">Track your learning journey</p>
        </div>

        {/* Error banner */}
        {loadError && (
          <div className="mx-8 mt-6 p-4 rounded-lg bg-[#FEE2E2] border border-[#DC2626]/30 text-sm text-[#991B1B]">
            {loadError}
          </div>
        )}

        {/* Main Content */}
        <div className="p-8 max-w-7xl">
          {/* Overall Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-xl p-6 shadow-edu-sm">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <p className="text-sm text-[#6B7280] mb-1">Overall Completion</p>
                  <p className="text-2xl font-bold text-[#111827]">
                    {loading ? '—' : `${Math.round(progress?.completionRate ?? 0)}%`}
                  </p>
                  {!loading && progress && (
                    <p className="text-xs text-[#6B7280] mt-1">
                      {progress.completedTopicsCount} / {progress.totalTopics} topics
                    </p>
                  )}
                </div>
                <CircularProgress
                  percentage={loading ? 0 : Math.round(progress?.completionRate ?? 0)}
                  size="small"
                />
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-edu-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-[#6B7280] mb-1">Quizzes Completed</p>
                  <p className="text-2xl font-bold text-[#111827]">
                    {loading ? '—' : progress?.quizzesCompleted ?? 0}
                  </p>
                  {!loading && progress?.quizAverage != null && (
                    <p className="text-xs text-[#6B7280] mt-1">
                      Avg: {Math.round(progress.quizAverage)}%
                    </p>
                  )}
                </div>
                <div className="w-12 h-12 bg-[#FEF3C7] rounded-full flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-[#F59E0B]" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-edu-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-[#6B7280] mb-1">Topics Bookmarked</p>
                  <p className="text-2xl font-bold text-[#111827]">
                    {loading ? '—' : progress?.bookmarkedTopicsCount ?? 0}
                  </p>
                </div>
                <div className="w-12 h-12 bg-[#EDE9FE] rounded-full flex items-center justify-center">
                  <Award className="w-6 h-6 text-[#7C3AED]" />
                </div>
              </div>
            </div>
          </div>

          {/* Learning Streak */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-8">
            <h2 className="text-xl font-bold text-[#111827] mb-4">Quiz Activity (Last 30 Days)</h2>
            <div className="flex gap-1 overflow-x-auto pb-2">
              {heatmapDays.map((day, i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded flex-shrink-0 transition-default hover:ring-2 hover:ring-[#1E3A8A] cursor-pointer"
                  style={{ backgroundColor: day.active ? '#059669' : '#E5E7EB' }}
                  title={day.date}
                />
              ))}
            </div>
            <p className="text-sm text-[#6B7280] mt-4">
              Current streak:{' '}
              <span className="font-bold text-[#F59E0B]">
                {streakDays} day{streakDays === 1 ? '' : 's'}{streakDays > 0 ? ' 🔥' : ''}
              </span>
            </p>
          </div>

          {/* Topic Completion by Chapter */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-8">
            <h2 className="text-xl font-bold text-[#111827] mb-6">Topic Completion by Chapter</h2>
            {loading ? (
              <p className="text-sm text-[#6B7280]">Loading...</p>
            ) : (progress?.byChapter ?? []).length === 0 ? (
              <p className="text-sm text-[#6B7280]">No chapters found.</p>
            ) : (
              <div className="space-y-4">
                {(progress?.byChapter ?? []).map((chapter) => {
                  const pct =
                    chapter.totalTopics > 0
                      ? Math.round((chapter.completedTopics / chapter.totalTopics) * 100)
                      : 0;
                  return (
                    <div key={`${chapter.formLevel}-${chapter.chapterId}`}>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="font-medium text-[#111827]">
                          Form {chapter.formLevel} — Bab {chapter.chapterId}
                        </span>
                        <span className="text-[#6B7280]">
                          {chapter.completedTopics}/{chapter.totalTopics} ({pct}%)
                        </span>
                      </div>
                      <div className="h-3 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-[#1E3A8A] to-[#3B82F6] rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <p className="text-xs text-[#6B7280] mt-1">{chapter.chapterName}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Quiz Performance Trend */}
            <div className="bg-white rounded-xl shadow-edu-sm p-6">
              <h2 className="text-xl font-bold text-[#111827] mb-6">Quiz Performance</h2>
              {recentAttempts.length === 0 ? (
                <div className="text-center py-6">
                  <p className="text-sm text-[#6B7280]">No submitted quizzes yet.</p>
                  <button
                    onClick={() => onNavigate('quiz-selection')}
                    className="mt-3 text-sm text-[#1E3A8A] font-medium hover:underline"
                  >
                    Take a quiz →
                  </button>
                </div>
              ) : (
                <>
                  <div className="space-y-3">
                    {recentAttempts.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-3 cursor-pointer hover:bg-[#F9FAFB] rounded-lg p-1 -mx-1 transition-default"
                        onClick={() =>
                          onNavigate('quiz-results', {
                            attemptId: String(item.attemptId),
                            quizId: String(item.quizId),
                          })
                        }
                        title={item.date}
                      >
                        <span className="text-xs text-[#6B7280] w-14 shrink-0 truncate" title={item.label}>
                          {item.date}
                        </span>
                        <div className="flex-1 h-7 bg-[#E5E7EB] rounded-full overflow-hidden">
                          {item.score != null ? (
                            <div
                              className="h-full bg-gradient-to-r from-[#059669] to-[#10B981] rounded-full flex items-center justify-end pr-3 transition-all"
                              style={{ width: `${item.score}%` }}
                            >
                              <span className="text-xs font-bold text-white">{item.score}%</span>
                            </div>
                          ) : (
                            <div className="h-full flex items-center pl-3">
                              <span className="text-xs text-[#9CA3AF]">No score</span>
                            </div>
                          )}
                        </div>
                        <span className="text-xs text-[#9CA3AF] w-32 shrink-0 truncate hidden lg:block" title={item.label}>
                          {item.label}
                        </span>
                      </div>
                    ))}
                  </div>
                  {recentAttempts.length >= 2 && (() => {
                    const scores = recentAttempts.map((r) => r.score).filter((s) => s != null) as number[];
                    if (scores.length < 2) return null;
                    const delta = scores[scores.length - 1] - scores[0];
                    return (
                      <p className={`text-sm mt-4 flex items-center gap-1 ${delta >= 0 ? 'text-[#059669]' : 'text-[#DC2626]'}`}>
                        <TrendingUp className="w-4 h-4" />
                        {delta >= 0 ? '+' : ''}{delta}% over last {scores.length} quizzes
                      </p>
                    );
                  })()}
                </>
              )}
            </div>

            {/* Focus Areas */}
            <div className="bg-white rounded-xl shadow-edu-sm p-6">
              <h2 className="text-xl font-bold text-[#111827] mb-6">Focus Areas</h2>
              {focusChapters.length === 0 ? (
                <p className="text-sm text-[#059669] font-medium">
                  All chapters are on track. Keep it up!
                </p>
              ) : (
                <div className="space-y-4">
                  {focusChapters.map((chapter) => {
                    const completionPct = chapter.totalTopics > 0
                      ? Math.round((chapter.completedTopics / chapter.totalTopics) * 100)
                      : 0;
                    const quizPct = chapter.quizAverage != null
                      ? Math.round(chapter.quizAverage)
                      : null;

                    const lowCompletion = completionPct < 50;
                    const lowQuiz = quizPct != null && quizPct < 70;
                    const lowEssay = chapter.essayAverage != null && chapter.essayAverage < 70;
                    const reason =
                      lowCompletion && lowQuiz && lowEssay ? 'Low completion, quiz & essay scores' :
                      lowCompletion && lowQuiz ? 'Low completion & quiz score' :
                      lowCompletion && lowEssay ? 'Low completion & essay score' :
                      lowQuiz && lowEssay ? 'Low quiz & essay scores' :
                      lowQuiz ? 'Low quiz score' :
                      lowEssay ? 'Low essay score' :
                      'Low topic completion';

                    const quizColor =
                      quizPct == null ? null :
                      quizPct < 60  ? { bg: '#FEE2E2', text: '#DC2626' } :
                      quizPct < 70  ? { bg: '#FEF3C7', text: '#D97706' } :
                                      { bg: '#D1FAE5', text: '#059669' };

                    return (
                      <div
                        key={`${chapter.formLevel}-${chapter.chapterId}`}
                        className="border border-[#E5E7EB] rounded-lg p-4"
                      >
                        <div className="flex justify-between items-start mb-1">
                          <div className="flex-1 min-w-0 mr-3">
                            <h3 className="font-medium text-[#111827] truncate">{chapter.chapterName}</h3>
                            <p className="text-xs text-[#6B7280]">
                              Bab {chapter.chapterId} — Form {chapter.formLevel}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1 shrink-0">
                            <span className="px-2 py-0.5 bg-[#FEE2E2] text-[#DC2626] text-xs font-medium rounded">
                              Topik {completionPct}%
                            </span>
                            {quizPct != null && quizColor ? (
                              <span
                                className="px-2 py-0.5 text-xs font-medium rounded"
                                style={{ backgroundColor: quizColor.bg, color: quizColor.text }}
                              >
                                Kuiz {quizPct}%
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 bg-[#F3F4F6] text-[#6B7280] text-xs rounded">
                                No quiz yet
                              </span>
                            )}
                          </div>
                        </div>
                        <p className="text-xs text-[#9CA3AF] mb-3">{reason}</p>
                        <Button
                          onClick={() =>
                            onNavigate('topics', {
                              formLevel: String(chapter.formLevel),
                              chapterId: String(chapter.chapterId),
                            })
                          }
                          size="sm"
                          variant="outline"
                          className="w-full"
                        >
                          Study Now
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Achievements */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mt-8">
            <h2 className="text-xl font-bold text-[#111827] mb-6">Achievements</h2>

            {/* Quiz achievements */}
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide mb-3">Quiz</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {achievements.filter((a) => a.group === 'quiz').map((a, idx) => (
                <AchievementCard key={idx} achievement={a} />
              ))}
            </div>

            {/* Essay achievements */}
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wide mb-3">Essay</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {achievements.filter((a) => a.group === 'essay').map((a, idx) => (
                <AchievementCard key={idx} achievement={a} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
