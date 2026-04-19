import { BookOpen, TrendingUp, FileText, Target, PlayCircle, MessageSquare, PenTool, Grid, Clock, CheckCircle } from 'lucide-react';
import { AppSidebar } from '../components/AppSidebar';
import { StatsCard } from '../components/StatsCard';
import { CircularProgress } from '../components/CircularProgress';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';

interface DashboardProps {
  onNavigate: (page: any, params?: any) => void;
}

export function Dashboard({ onNavigate }: DashboardProps) {
  const currentHour = new Date().getHours();
  const greeting =
    currentHour < 12 ? 'Selamat Pagi' : currentHour < 18 ? 'Selamat Petang' : 'Selamat Malam';

  const stats = [
    {
      icon: BookOpen,
      iconColor: '#059669',
      iconBgColor: '#D1FAE5',
      label: 'Topics Completed',
      value: '12/35',
      trend: { direction: 'up' as const, value: '+3 this week' },
    },
    {
      icon: Target,
      iconColor: '#1E3A8A',
      iconBgColor: '#DBEAFE',
      label: 'Quiz Average',
      value: '78%',
      trend: { direction: 'up' as const, value: '+5% from last week' },
    },
    {
      icon: TrendingUp,
      iconColor: '#F59E0B',
      iconBgColor: '#FEF3C7',
      label: 'Study Streak',
      value: '5 days',
      trend: { direction: 'up' as const, value: 'Keep it going!' },
    },
    {
      icon: FileText,
      iconColor: '#7C3AED',
      iconBgColor: '#EDE9FE',
      label: 'Essays Practiced',
      value: '8',
      trend: { direction: 'up' as const, value: '+2 this week' },
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

  const recentActivities = [
    {
      icon: CheckCircle,
      iconColor: '#059669',
      title: 'Completed Quiz: Tamadun Awal',
      time: '2 hours ago',
    },
    {
      icon: BookOpen,
      iconColor: '#1E3A8A',
      title: 'Studied: Kesultanan Melayu Melaka',
      time: '5 hours ago',
    },
    {
      icon: FileText,
      iconColor: '#7C3AED',
      title: 'Submitted Essay: Pendudukan Jepun',
      time: '1 day ago',
    },
    {
      icon: MessageSquare,
      iconColor: '#059669',
      title: 'Asked AI about Perlembagaan Persekutuan',
      time: '2 days ago',
    },
    {
      icon: CheckCircle,
      iconColor: '#059669',
      title: 'Completed Topic: Nationalism in Malaya',
      time: '3 days ago',
    },
  ];

  const recommendedTopics = [
    {
      id: '1',
      title: 'Peristiwa Bersejarah Dunia',
      chapter: 'Bab 2 - Form 5',
      progress: 45,
      thumbnail: '#F59E0B',
    },
    {
      id: '2',
      title: 'Kemerdekaan Tanah Melayu',
      chapter: 'Bab 3 - Form 5',
      progress: 0,
      thumbnail: '#1E3A8A',
    },
    {
      id: '3',
      title: 'Kerajaan Alam Melayu',
      chapter: 'Bab 6 - Form 4',
      progress: 80,
      thumbnail: '#059669',
    },
  ];

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="dashboard" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827] mb-1">
            {greeting}, Alimzhan! 👋
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
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {stats.map((stat, index) => (
              <StatsCard key={index} {...stat} />
            ))}
          </div>

          {/* Continue Learning Section */}
          <div className="mb-8">
            <h2 className="text-xl font-bold text-[#111827] mb-4">Continue Where You Left Off</h2>
            <div className="bg-white rounded-xl p-6 shadow-edu-sm hover:shadow-edu-md transition-default cursor-pointer">
              <div className="flex items-start gap-6">
                <div className="w-32 h-32 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-lg flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-16 h-16 text-white" />
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-lg font-bold text-[#111827] mb-1">
                        Tamadun Islam di Madinah
                      </h3>
                      <p className="text-sm text-[#6B7280]">Bab 5 - Form 4</p>
                    </div>
                    <CircularProgress percentage={65} size="small" />
                  </div>
                  <p className="text-sm text-[#6B7280] mb-4">
                    Learn about the establishment and development of Islamic civilization in Madinah
                  </p>
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-[#6B7280] mb-2">
                      <span>Progress</span>
                      <span>65%</span>
                    </div>
                    <Progress value={65} className="h-2" />
                  </div>
                  <Button
                    onClick={() => onNavigate('topic-content', { topicId: 'tamadun-islam' })}
                    className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
                  >
                    Continue Learning
                  </Button>
                </div>
              </div>
            </div>
          </div>

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
            {/* Recent Activity */}
            <div>
              <h2 className="text-xl font-bold text-[#111827] mb-4">Recent Activity</h2>
              <div className="bg-white rounded-xl p-6 shadow-edu-sm">
                <div className="space-y-4">
                  {recentActivities.map((activity, index) => {
                    const Icon = activity.icon;
                    return (
                      <div key={index} className="flex items-start gap-3">
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: `${activity.iconColor}20` }}
                        >
                          <Icon className="w-4 h-4" style={{ color: activity.iconColor }} />
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-[#111827]">{activity.title}</p>
                          <p className="text-xs text-[#6B7280] mt-0.5 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {activity.time}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Recommended Topics */}
            <div>
              <h2 className="text-xl font-bold text-[#111827] mb-4">Recommended for You</h2>
              <div className="space-y-4">
                {recommendedTopics.map((topic) => (
                  <div
                    key={topic.id}
                    className="bg-white rounded-xl p-4 shadow-edu-sm hover:shadow-edu-md transition-default cursor-pointer"
                    onClick={() => onNavigate('topic-content', { topicId: topic.id })}
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className="w-16 h-16 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: topic.thumbnail }}
                      >
                        <BookOpen className="w-8 h-8 text-white" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-bold text-[#111827] mb-1">{topic.title}</h3>
                        <p className="text-xs text-[#6B7280] mb-3">{topic.chapter}</p>
                        <div>
                          <div className="flex justify-between text-xs text-[#6B7280] mb-1">
                            <span>{topic.progress === 0 ? 'Not Started' : 'In Progress'}</span>
                            <span>{topic.progress}%</span>
                          </div>
                          <Progress value={topic.progress} className="h-1.5" />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}