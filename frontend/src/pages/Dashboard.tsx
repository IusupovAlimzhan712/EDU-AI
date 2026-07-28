import { useEffect, useState } from 'react';
import { BookOpen, TrendingUp, Target, PlayCircle, MessageSquare, PenTool, Grid, Clock, CheckCircle, Flame } from 'lucide-react';
import { AppSidebar } from '../components/AppSidebar';
import { StatsCard } from '../components/StatsCard';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
import { api, ProgressOverview, QuizAttempt } from '../lib/api';

interface DashboardProps {
  onNavigate: (page: any, params?: any) => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins || 1}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const { student } = useAuth();
  const currentHour = new Date().getHours();
  const greeting =
    currentHour < 12 ? 'Selamat Pagi' : currentHour < 18 ? 'Selamat Petang' : 'Selamat Malam';

  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [attempts, setAttempts] = useState<QuizAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getProgress(), api.listMyAttempts()])
      .then(([p, a]) => {
        setProgress(p);
        setAttempts(a);
      })
      .catch(() => setLoadError('Failed to load dashboard data. Please refresh the page.'))
      .finally(() => setLoading(false));
  }, []);

  const stats = [
    {
      icon: BookOpen,
      iconColor: '#059669',
      iconBgColor: '#D1FAE5',
      label: 'Topics Completed',
      value: loading
        ? '—'
        : progress
        ? `${progress.completedTopicsCount}/${progress.totalTopics}`
        : '—',
      trend: { direction: 'up' as const, value: loading ? '' : progress ? `${Math.round(progress.completionRate)}% done` : '' },
    },
    {
      icon: Target,
      iconColor: '#1E3A8A',
      iconBgColor: '#DBEAFE',
      label: 'Quiz Average',
      value: loading
        ? '—'
        : progress?.quizAverage != null
        ? `${Math.round(progress.quizAverage)}%`
        : '—',
      trend: {
        direction: 'up' as const,
        value: loading ? '' : progress?.quizzesCompleted ? `${progress.quizzesCompleted} quiz${progress.quizzesCompleted === 1 ? '' : 'zes'} done` : 'No quizzes yet',
      },
    },
    {
      icon: TrendingUp,
      iconColor: '#F59E0B',
      iconBgColor: '#FEF3C7',
      label: 'Best Quiz Score',
      value: loading
        ? '—'
        : progress?.bestQuizPercentage != null
        ? `${Math.round(progress.bestQuizPercentage)}%`
        : '—',
      trend: { direction: 'up' as const, value: 'Personal best' },
    },
    {
      icon: BookOpen,
      iconColor: '#7C3AED',
      iconBgColor: '#EDE9FE',
      label: 'Topics Bookmarked',
      value: loading ? '—' : progress ? String(progress.bookmarkedTopicsCount) : '—',
      trend: { direction: 'up' as const, value: 'Saved for later' },
    },
    {
      icon: Flame,
      iconColor: '#EA580C',
      iconBgColor: '#FFF7ED',
      label: 'Study Streak',
      value: loading ? '—' : progress ? `${progress.currentStreak} day${progress.currentStreak === 1 ? '' : 's'}` : '—',
      trend: {
        direction: 'up' as const,
        value: loading ? '' : progress?.currentStreak
          ? `Keep it up!`
          : 'Complete a topic to start',
      },
    },
  ];

  const quickActions = [
    {
      title: 'Start Quiz',
      description: 'Test your knowledge',
      icon: PlayCircle,
      color: '#1E3A8A',
      bgColor: '#EFF6FF',
      action: 'quiz-selection',
    },
    {
      title: 'Ask AI Tutor',
      description: 'Get instant help',
      icon: MessageSquare,
      color: '#059669',
      bgColor: '#ECFDF5',
      action: 'ai-tutor',
    },
    {
      title: 'Essay Practice',
      description: 'Improve writing skills',
      icon: PenTool,
      color: '#7C3AED',
      bgColor: '#F5F3FF',
      action: 'essay-practice',
    },
    {
      title: 'Browse Topics',
      description: 'Explore syllabus',
      icon: Grid,
      color: '#F59E0B',
      bgColor: '#FFFBEB',
      action: 'topics',
    },
  ];

  // Recent activity: submitted attempts (newest first, up to 5)
  const recentSubmissions = attempts
    .filter((a) => a.status === 'submitted' && a.submittedAt)
    .slice(0, 5);

  // In-progress attempt (for "continue" banner)
  const inProgressAttempt = attempts.find((a) => a.status === 'in_progress');

  // Chapters with no completed topics yet (up to 3) — for recommendations
  const suggestedChapters = (progress?.byChapter ?? [])
    .filter((c) => c.completedTopics === 0)
    .slice(0, 3);

  const thumbnailColors = ['#F59E0B', '#1E3A8A', '#059669', '#7C3AED'];

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="dashboard" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827] mb-1">
            {greeting}, {student?.fullName ?? 'Student'}! 👋
          </h1>
          <p className="text-[#6B7280]">Ready to continue your Sejarah journey?</p>
          <p className="text-sm text-[#6B7280] mt-1">
            {new Date().toLocaleDateString('en-MY', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>

        {/* Main Content */}
        <div className="p-8 max-w-7xl">
          {loadError && (
            <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
              {loadError}
            </div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8">
            {stats.map((stat, index) => (
              <StatsCard key={index} {...stat} />
            ))}
          </div>

          {/* Continue Learning — only shown if there's an in-progress attempt */}
          {inProgressAttempt && (
            <div className="mb-8">
              <h2 className="text-xl font-bold text-[#111827] mb-4">Continue Where You Left Off</h2>
              <div className="bg-white rounded-xl p-6 shadow-edu-sm hover:shadow-edu-md transition-default cursor-pointer">
                <div className="flex items-center gap-6">
                  <div className="w-16 h-16 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-lg flex items-center justify-center flex-shrink-0">
                    <Target className="w-8 h-8 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[#111827]">
                      {inProgressAttempt.quizTitle ?? 'Sejarah Quiz'}
                    </p>
                    <p className="text-xs text-[#9CA3AF]">
                      Started {timeAgo(inProgressAttempt.startedAt)}
                    </p>
                  </div>
                  <Button
                    onClick={() => onNavigate('quiz-in-progress', { attemptId: String(inProgressAttempt.attemptId) })}
                    className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
                  >
                    Resume Quiz
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Quick Actions Grid */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-[#111827] mb-4">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {quickActions.map((action, index) => {
                const Icon = action.icon;
                return (
                  <button
                    key={index}
                    onClick={() => onNavigate(action.action)}
                    className="bg-white rounded-xl p-6 shadow-edu-sm hover:shadow-edu-md transition-default text-left group"
                  >
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-default"
                      style={{ backgroundColor: action.bgColor }}
                    >
                      <Icon className="w-6 h-6" style={{ color: action.color }} />
                    </div>
                    <h3 className="font-bold text-[#111827] mb-1">{action.title}</h3>
                    <p className="text-sm text-[#6B7280]">{action.description}</p>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Recent Quiz Activity */}
            <div>
              <h2 className="text-xl font-bold text-[#111827] mb-4">Recent Quiz Activity</h2>
              <div className="bg-white rounded-xl p-6 shadow-edu-sm">
                {recentSubmissions.length === 0 ? (
                  <div className="text-center py-6">
                    <Target className="w-10 h-10 text-[#D1D5DB] mx-auto mb-3" />
                    <p className="text-sm text-[#6B7280]">No quizzes completed yet.</p>
                    <button
                      onClick={() => onNavigate('quiz-selection')}
                      className="mt-3 text-sm text-[#1E3A8A] font-medium hover:underline"
                    >
                      Take your first quiz →
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {recentSubmissions.map((attempt) => {
                      const pct =
                        attempt.score != null && attempt.maxScore && attempt.maxScore > 0
                          ? Math.round((attempt.score / attempt.maxScore) * 100)
                          : null;
                      const color = pct == null ? '#6B7280' : pct >= 70 ? '#059669' : '#DC2626';
                      return (
                        <div
                          key={attempt.attemptId}
                          className="flex items-start gap-3 cursor-pointer hover:bg-[#F9FAFB] rounded-lg p-2 -mx-2 transition-default"
                          onClick={() =>
                            onNavigate('quiz-results', {
                              attemptId: String(attempt.attemptId),
                              quizId: String(attempt.quizId),
                            })
                          }
                        >
                          <div
                            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                            style={{ backgroundColor: `${color}20` }}
                          >
                            <CheckCircle className="w-4 h-4" style={{ color }} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-[#111827] truncate">
                              {attempt.quizTitle ?? 'Sejarah Quiz'}
                              {pct != null && (
                                <span
                                  className="ml-2 px-2 py-0.5 rounded text-xs font-bold"
                                  style={{ backgroundColor: `${color}20`, color }}
                                >
                                  {pct}%
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-[#6B7280] mt-0.5 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {attempt.submittedAt ? timeAgo(attempt.submittedAt) : '—'}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Chapters to Explore */}
            <div>
              <h2 className="text-xl font-bold text-[#111827] mb-4">
                {suggestedChapters.length > 0 ? 'Chapters to Explore' : 'Your Progress by Chapter'}
              </h2>
              {suggestedChapters.length > 0 ? (
                <div className="space-y-4">
                  {suggestedChapters.map((chapter, i) => (
                    <div
                      key={`${chapter.formLevel}-${chapter.chapterId}`}
                      className="bg-white rounded-xl p-4 shadow-edu-sm hover:shadow-edu-md transition-default cursor-pointer"
                      onClick={() =>
                        onNavigate('topics', {
                          formLevel: String(chapter.formLevel),
                          chapterId: String(chapter.chapterId),
                        })
                      }
                    >
                      <div className="flex items-start gap-4">
                        <div
                          className="w-16 h-16 rounded-lg flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: thumbnailColors[i % thumbnailColors.length] }}
                        >
                          <BookOpen className="w-8 h-8 text-white" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-bold text-[#111827] mb-1">{chapter.chapterName}</h3>
                          <p className="text-xs text-[#6B7280] mb-2">
                            Bab {chapter.chapterId} — Form {chapter.formLevel}
                          </p>
                          <p className="text-xs text-[#6B7280]">
                            {chapter.totalTopics} topic{chapter.totalTopics === 1 ? '' : 's'} · Not started
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-white rounded-xl p-6 shadow-edu-sm">
                  <p className="text-sm text-[#059669] font-medium mb-2">
                    Great work! You've started every chapter.
                  </p>
                  <button
                    onClick={() => onNavigate('progress')}
                    className="text-sm text-[#1E3A8A] hover:underline"
                  >
                    View full progress →
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
