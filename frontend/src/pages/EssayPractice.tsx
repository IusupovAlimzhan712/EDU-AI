import { AppSidebar } from '../components/AppSidebar';
import { Button } from '../components/ui/button';
import { DifficultyBadge } from '../components/DifficultyBadge';
import { FormLevelBadge } from '../components/FormLevelBadge';
import { PencilLine, Award } from 'lucide-react';

interface EssayPracticeProps {
  onNavigate: (page: any, params?: any) => void;
}

const essays = [
  {
    id: '1',
    type: 'Soalan Struktur',
    marks: 10,
    question: 'Huraikan faktor-faktor kejatuhan Kesultanan Melayu Melaka.',
    form: 4,
    chapter: 'Bab 6',
    difficulty: 'medium' as const,
    attempted: true,
    score: 7,
  },
  {
    id: '2',
    type: 'Soalan Esei',
    marks: 20,
    question: 'Bincangkan kesan-kesan pendudukan Jepun terhadap masyarakat di Tanah Melayu.',
    form: 5,
    chapter: 'Bab 1',
    difficulty: 'hard' as const,
    attempted: true,
    score: 15,
  },
  {
    id: '3',
    type: 'Soalan Struktur',
    marks: 8,
    question: 'Jelaskan peranan Piagam Madinah dalam pembentukan masyarakat Islam.',
    form: 4,
    chapter: 'Bab 5',
    difficulty: 'easy' as const,
    attempted: false,
  },
];

export function EssayPractice({ onNavigate }: EssayPracticeProps) {
  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="essay-practice" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827] mb-1">Essay Practice</h1>
          <p className="text-[#6B7280]">Practice SPM-style structured and essay questions</p>
        </div>

        {/* Main Content */}
        <div className="p-8 max-w-6xl">
          {/* Essay Question Cards */}
          <div className="space-y-4">
            {essays.map((essay) => (
              <div
                key={essay.id}
                className="bg-white rounded-xl shadow-edu-sm hover:shadow-edu-md transition-default p-6"
              >
                <div className="flex items-start gap-6">
                  <div
                    className={`w-16 h-16 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      essay.type === 'Soalan Struktur'
                        ? 'bg-[#DBEAFE]'
                        : 'bg-[#EDE9FE]'
                    }`}
                  >
                    <PencilLine
                      className={`w-8 h-8 ${
                        essay.type === 'Soalan Struktur'
                          ? 'text-[#1E3A8A]'
                          : 'text-[#7C3AED]'
                      }`}
                    />
                  </div>

                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${
                            essay.type === 'Soalan Struktur'
                              ? 'bg-[#DBEAFE] text-[#1E3A8A]'
                              : 'bg-[#EDE9FE] text-[#7C3AED]'
                          }`}
                        >
                          {essay.type}
                        </span>
                        <span className="px-3 py-1 bg-[#F3F4F6] text-[#6B7280] rounded-full text-xs font-medium">
                          [{essay.marks} marks]
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <FormLevelBadge form={essay.form as 4 | 5} />
                        <DifficultyBadge difficulty={essay.difficulty} />
                      </div>
                    </div>

                    <p className="text-lg font-medium text-[#111827] mb-2">{essay.question}</p>
                    <p className="text-sm text-[#6B7280] mb-4">{essay.chapter}</p>

                    <div className="flex items-center justify-between">
                      <div>
                        {essay.attempted && (
                          <div className="flex items-center gap-2 text-sm">
                            <Award className="w-4 h-4 text-[#F59E0B]" />
                            <span className="text-[#6B7280]">Previous Score:</span>
                            <span className="font-bold text-[#059669]">
                              {essay.score}/{essay.marks}
                            </span>
                          </div>
                        )}
                      </div>
                      <Button
                        onClick={() => onNavigate('essay-writing', { essayId: essay.id })}
                        className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
                      >
                        {essay.attempted ? 'Try Again' : 'Practice Now'}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
