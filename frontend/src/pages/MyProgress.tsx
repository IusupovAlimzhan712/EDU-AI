import { AppSidebar } from '../components/AppSidebar';
import { CircularProgress } from '../components/CircularProgress';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { TrendingUp, Clock, Award } from 'lucide-react';

interface MyProgressProps {
  onNavigate: (page: any) => void;
}

const topicProgress = [
  { chapter: 'Form 4 - Bab 1', name: 'Kemunculan Tamadun Awal Manusia', completion: 100 },
  { chapter: 'Form 4 - Bab 2', name: 'Peningkatan Tamadun', completion: 75 },
  { chapter: 'Form 4 - Bab 3', name: 'Tamadun Awal Asia Tenggara', completion: 50 },
  { chapter: 'Form 4 - Bab 5', name: 'Kerajaan Islam di Madinah', completion: 65 },
  { chapter: 'Form 5 - Bab 1', name: 'Warisan Negara Bangsa', completion: 45 },
  { chapter: 'Form 5 - Bab 3', name: 'Kemerdekaan Tanah Melayu', completion: 80 },
];

const quizScores = [
  { date: 'Week 1', score: 65 },
  { date: 'Week 2', score: 72 },
  { date: 'Week 3', score: 78 },
  { date: 'Week 4', score: 82 },
];

const weakAreas = [
  { topic: 'Tamadun Mesopotamia', score: 45, chapter: 'Bab 2' },
  { topic: 'Pendudukan Jepun', score: 55, chapter: 'Bab 1 - Form 5' },
  { topic: 'Penyebaran Islam', score: 60, chapter: 'Bab 7' },
];

const achievements = [
  { title: 'First Quiz Completed', icon: '🎯', date: '2 weeks ago' },
  { title: '7-Day Streak', icon: '🔥', date: '1 week ago' },
  { title: '100% Chapter Completion', icon: '⭐', date: '3 days ago' },
  { title: '10 Essays Practiced', icon: '📝', date: 'Today' },
];

export function MyProgress({ onNavigate }: MyProgressProps) {
  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="progress" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-[#111827] mb-1">My Progress</h1>
              <p className="text-[#6B7280]">Track your learning journey</p>
            </div>
            <Select defaultValue="all">
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="month">This Month</SelectItem>
                <SelectItem value="week">This Week</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Main Content */}
        <div className="p-8 max-w-7xl">
          {/* Overall Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-xl p-6 shadow-edu-sm">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <p className="text-sm text-[#6B7280] mb-1">Overall Completion</p>
                  <p className="text-2xl font-bold text-[#111827]">34%</p>
                </div>
                <CircularProgress percentage={34} size="small" />
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-edu-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-[#6B7280] mb-1">Total Study Time</p>
                  <p className="text-2xl font-bold text-[#111827]">24h</p>
                </div>
                <div className="w-12 h-12 bg-[#DBEAFE] rounded-full flex items-center justify-center">
                  <Clock className="w-6 h-6 text-[#1E3A8A]" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-edu-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-[#6B7280] mb-1">Quizzes Completed</p>
                  <p className="text-2xl font-bold text-[#111827]">18</p>
                </div>
                <div className="w-12 h-12 bg-[#FEF3C7] rounded-full flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-[#F59E0B]" />
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-edu-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-[#6B7280] mb-1">Essays Practiced</p>
                  <p className="text-2xl font-bold text-[#111827]">8</p>
                </div>
                <div className="w-12 h-12 bg-[#EDE9FE] rounded-full flex items-center justify-center">
                  <Award className="w-6 h-6 text-[#7C3AED]" />
                </div>
              </div>
            </div>
          </div>

          {/* Learning Streak */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-8">
            <h2 className="text-xl font-bold text-[#111827] mb-4">Learning Streak</h2>
            <div className="flex gap-1 overflow-x-auto pb-2">
              {Array.from({ length: 30 }).map((_, i) => {
                const intensity = Math.random();
                const hasActivity = intensity > 0.3;
                return (
                  <div
                    key={i}
                    className="w-8 h-8 rounded flex-shrink-0 transition-default hover:ring-2 hover:ring-[#1E3A8A] cursor-pointer"
                    style={{
                      backgroundColor: hasActivity
                        ? `rgba(5, 150, 105, ${intensity})`
                        : '#E5E7EB',
                    }}
                    title={`Day ${i + 1}`}
                  />
                );
              })}
            </div>
            <p className="text-sm text-[#6B7280] mt-4">
              Current streak: <span className="font-bold text-[#F59E0B]">5 days 🔥</span>
            </p>
          </div>

          {/* Topic Completion Chart */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-8">
            <h2 className="text-xl font-bold text-[#111827] mb-6">Topic Completion by Chapter</h2>
            <div className="space-y-4">
              {topicProgress.map((topic, idx) => (
                <div key={idx}>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-[#111827]">{topic.chapter}</span>
                    <span className="text-[#6B7280]">{topic.completion}%</span>
                  </div>
                  <div className="h-3 bg-[#E5E7EB] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-[#1E3A8A] to-[#3B82F6] rounded-full transition-all"
                      style={{ width: `${topic.completion}%` }}
                    />
                  </div>
                  <p className="text-xs text-[#6B7280] mt-1">{topic.name}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Performance Over Time */}
            <div className="bg-white rounded-xl shadow-edu-sm p-6">
              <h2 className="text-xl font-bold text-[#111827] mb-6">Quiz Performance Trend</h2>
              <div className="space-y-4">
                {quizScores.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-4">
                    <span className="text-sm font-medium text-[#6B7280] w-20">{item.date}</span>
                    <div className="flex-1 h-8 bg-[#E5E7EB] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#059669] to-[#10B981] rounded-full flex items-center justify-end pr-3 transition-all"
                        style={{ width: `${item.score}%` }}
                      >
                        <span className="text-xs font-bold text-white">{item.score}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-sm text-[#059669] mt-4 flex items-center gap-1">
                <TrendingUp className="w-4 h-4" />
                +17% improvement this month
              </p>
            </div>

            {/* Weak Areas */}
            <div className="bg-white rounded-xl shadow-edu-sm p-6">
              <h2 className="text-xl font-bold text-[#111827] mb-6">Focus Areas</h2>
              <div className="space-y-4">
                {weakAreas.map((area, idx) => (
                  <div key={idx} className="border border-[#E5E7EB] rounded-lg p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h3 className="font-medium text-[#111827]">{area.topic}</h3>
                        <p className="text-xs text-[#6B7280]">{area.chapter}</p>
                      </div>
                      <span className="px-2 py-1 bg-[#FEE2E2] text-[#DC2626] text-xs font-medium rounded">
                        {area.score}%
                      </span>
                    </div>
                    <Button
                      onClick={() => onNavigate('topics')}
                      size="sm"
                      variant="outline"
                      className="w-full"
                    >
                      Practice
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Achievements */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mt-8">
            <h2 className="text-xl font-bold text-[#111827] mb-6">Recent Achievements</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {achievements.map((achievement, idx) => (
                <div key={idx} className="border border-[#E5E7EB] rounded-lg p-4 text-center">
                  <div className="text-4xl mb-2">{achievement.icon}</div>
                  <h3 className="font-medium text-[#111827] mb-1">{achievement.title}</h3>
                  <p className="text-xs text-[#6B7280]">{achievement.date}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
