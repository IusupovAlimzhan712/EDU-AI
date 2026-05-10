import { AppSidebar } from '../components/AppSidebar';
import { Button } from '../components/ui/button';
import { DifficultyBadge } from '../components/DifficultyBadge';
import { FormLevelBadge } from '../components/FormLevelBadge';
import { StatusBadge } from '../components/StatusBadge';
import { PlayCircle, Clock, HelpCircle, Plus } from 'lucide-react';

interface QuizSelectionProps {
  onNavigate: (page: any, params?: any) => void;
}

const quizzes = [
  {
    id: '1',
    title: 'Tamadun Awal Manusia',
    chapter: 'Bab 1',
    form: 4,
    difficulty: 'easy' as const,
    questions: 10,
    duration: '10 min',
    bestScore: '8/10',
    attempts: 2,
    status: 'completed' as const,
  },
  {
    id: '2',
    title: 'Kerajaan Islam di Madinah',
    chapter: 'Bab 5',
    form: 4,
    difficulty: 'medium' as const,
    questions: 15,
    duration: '15 min',
    bestScore: '10/15',
    attempts: 1,
    status: 'in-progress' as const,
  },
  {
    id: '3',
    title: 'Pendudukan Jepun',
    chapter: 'Bab 1',
    form: 5,
    difficulty: 'hard' as const,
    questions: 20,
    duration: '20 min',
    bestScore: null,
    attempts: 0,
    status: 'not-started' as const,
  },
  {
    id: '4',
    title: 'Kemerdekaan Tanah Melayu',
    chapter: 'Bab 3',
    form: 5,
    difficulty: 'medium' as const,
    questions: 12,
    duration: '12 min',
    bestScore: '9/12',
    attempts: 3,
    status: 'completed' as const,
  },
];

export function QuizSelection({ onNavigate }: QuizSelectionProps) {
  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="quiz-selection" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827] mb-1">Quizzes</h1>
          <p className="text-[#6B7280]">You've completed 4 quizzes this week</p>
        </div>

        {/* Main Content */}
        <div className="p-8 max-w-7xl">
          {/* Create Custom Quiz Card */}
          <div className="bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-xl p-8 mb-8 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold mb-2">Create Custom Quiz</h2>
                <p className="text-blue-100 mb-4">
                  Select specific topics to test yourself
                </p>
              </div>
              <Button className="bg-white text-[#1E3A8A] hover:bg-blue-50">
                <Plus className="w-4 h-4 mr-2" />
                Create Quiz
              </Button>
            </div>
          </div>

          {/* Quiz Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {quizzes.map((quiz) => (
              <div
                key={quiz.id}
                className="bg-white rounded-xl shadow-edu-sm hover:shadow-edu-md transition-default overflow-hidden"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div
                      className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                        quiz.difficulty === 'easy'
                          ? 'bg-[#D1FAE5]'
                          : quiz.difficulty === 'medium'
                          ? 'bg-[#FEF3C7]'
                          : 'bg-[#FEE2E2]'
                      }`}
                    >
                      <HelpCircle
                        className={`w-6 h-6 ${
                          quiz.difficulty === 'easy'
                            ? 'text-[#059669]'
                            : quiz.difficulty === 'medium'
                            ? 'text-[#D97706]'
                            : 'text-[#DC2626]'
                        }`}
                      />
                    </div>
                    <div className="flex gap-2">
                      <FormLevelBadge form={quiz.form as 4 | 5} />
                    </div>
                  </div>

                  <h3 className="font-bold text-[#111827] mb-2">{quiz.title}</h3>
                  <p className="text-sm text-[#6B7280] mb-4">{quiz.chapter}</p>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-[#6B7280]">Questions:</span>
                      <span className="font-medium text-[#111827]">{quiz.questions}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-[#6B7280]">Duration:</span>
                      <span className="font-medium text-[#111827] flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {quiz.duration}
                      </span>
                    </div>
                    {quiz.bestScore && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[#6B7280]">Best Score:</span>
                        <span className="font-medium text-[#059669]">{quiz.bestScore}</span>
                      </div>
                    )}
                    {quiz.attempts > 0 && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[#6B7280]">Attempts:</span>
                        <span className="font-medium text-[#111827]">{quiz.attempts}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between mb-4">
                    <DifficultyBadge difficulty={quiz.difficulty} />
                    <StatusBadge status={quiz.status} />
                  </div>

                  <Button
                    onClick={() => onNavigate('quiz-in-progress', { quizId: quiz.id })}
                    className="w-full bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
                  >
                    <PlayCircle className="w-4 h-4 mr-2" />
                    {quiz.attempts > 0 ? 'Retry Quiz' : 'Start Quiz'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
