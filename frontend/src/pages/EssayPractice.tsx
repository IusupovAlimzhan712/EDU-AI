import { useState, useEffect } from 'react';
import { AppSidebar } from '../components/AppSidebar';
import { Button } from '../components/ui/button';
import { DifficultyBadge } from '../components/DifficultyBadge';
import { FormLevelBadge } from '../components/FormLevelBadge';
import { PencilLine, Award, Loader2 } from 'lucide-react';
import { api, EssayQuestion } from '../lib/api';
import { useAuth } from '../context/AuthContext';

interface EssayPracticeProps {
  onNavigate: (page: any, params?: any) => void;
}

export function EssayPractice({ onNavigate }: EssayPracticeProps) {
  const { student } = useAuth();
  const [questions, setQuestions] = useState<EssayQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterChapter, setFilterChapter] = useState<number | null>(null);
  const [filterDifficulty, setFilterDifficulty] = useState<string | null>(null);

  useEffect(() => {
    const formLevel = student?.formLevel;
    api.listEssayQuestions(formLevel ? { formLevel } : {})
      .then(setQuestions)
      .catch((err) => setError(err.message ?? 'Failed to load essay questions.'))
      .finally(() => setLoading(false));
  }, [student?.formLevel]);

  // Derive chapters from questions matching the current difficulty filter only,
  // so the chapter dropdown stays in sync with visible questions.
  const chaptersForDifficulty = filterDifficulty !== null
    ? questions.filter((q) => q.difficulty === filterDifficulty)
    : questions;
  const availableChapters = [...new Set(chaptersForDifficulty.map((q) => q.chapterId))].sort((a, b) => a - b);

  // Client-side filter
  const filtered = questions.filter((q) => {
    if (filterChapter !== null && q.chapterId !== filterChapter) return false;
    if (filterDifficulty !== null && q.difficulty !== filterDifficulty) return false;
    return true;
  });

  const grouped = filtered.reduce<Record<string, EssayQuestion[]>>((acc, q) => {
    const key = `F${q.formLevel}-Bab ${q.chapterId}: ${q.chapterName}`;
    (acc[key] = acc[key] ?? []).push(q);
    return acc;
  }, {});

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="essay-practice" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827] mb-1">Essay Practice</h1>
          <p className="text-[#6B7280] mb-4">Practice SPM Sejarah Kertas 2 structured and essay questions</p>

          {/* Filters */}
          {!loading && !error && questions.length > 0 && (
            <div className="flex items-center gap-3 flex-wrap">
              <label className="text-sm font-medium text-[#374151]">Chapter:</label>
              <select
                value={filterChapter ?? ''}
                onChange={(e) => setFilterChapter(e.target.value === '' ? null : Number(e.target.value))}
                className="text-sm border border-[#D1D5DB] rounded-lg px-3 py-1.5 text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]"
              >
                <option value="">All Chapters</option>
                {availableChapters.map((cid) => (
                  <option key={cid} value={cid}>Bab {cid}</option>
                ))}
              </select>

              <label className="text-sm font-medium text-[#374151]">Difficulty:</label>
              <select
                value={filterDifficulty ?? ''}
                onChange={(e) => setFilterDifficulty(e.target.value === '' ? null : e.target.value)}
                className="text-sm border border-[#D1D5DB] rounded-lg px-3 py-1.5 text-[#374151] focus:outline-none focus:ring-2 focus:ring-[#1E3A8A]"
              >
                <option value="">All Difficulties</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>

              {(filterChapter !== null || filterDifficulty !== null) && (
                <button
                  onClick={() => { setFilterChapter(null); setFilterDifficulty(null); }}
                  className="text-sm text-[#6B7280] hover:text-[#374151] underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
        </div>

        <div className="p-8 max-w-6xl">
          {loading && (
            <div className="flex items-center justify-center py-20 text-[#6B7280]">
              <Loader2 className="w-6 h-6 animate-spin mr-3" />
              Loading questions…
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-6">
              {error}
            </div>
          )}

          {!loading && !error && questions.length === 0 && (
            <div className="bg-white rounded-xl shadow-edu-sm p-12 text-center text-[#6B7280]">
              <PencilLine className="w-12 h-12 mx-auto mb-4 text-[#D1D5DB]" />
              <p className="text-lg font-medium mb-2">Soalan sedang disediakan</p>
              <p className="text-sm">Essay questions for your form level are being generated. Please check back soon.</p>
            </div>
          )}

          {!loading && !error && questions.length > 0 && filtered.length === 0 && (
            <div className="bg-white rounded-xl shadow-edu-sm p-12 text-center text-[#6B7280]">
              <PencilLine className="w-12 h-12 mx-auto mb-4 text-[#D1D5DB]" />
              <p className="text-lg font-medium mb-2">No questions match your filters</p>
              <p className="text-sm mb-4">
                Try selecting a different chapter or difficulty level.
              </p>
              <button
                onClick={() => { setFilterChapter(null); setFilterDifficulty(null); }}
                className="text-sm text-[#1E3A8A] font-medium hover:underline"
              >
                Clear filters
              </button>
            </div>
          )}

          {Object.entries(grouped).map(([groupLabel, qs]) => (
            <div key={groupLabel} className="mb-8">
              <h2 className="text-sm font-semibold text-[#6B7280] uppercase tracking-wide mb-3">
                {groupLabel}
              </h2>
              <div className="space-y-4">
                {qs.map((q) => (
                  <QuestionCard key={q.questionId} question={q} onNavigate={onNavigate} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function QuestionCard({
  question,
  onNavigate,
}: {
  question: EssayQuestion;
  onNavigate: (page: any, params?: any) => void;
}) {
  const isStruktur = question.questionType === 'struktur';
  const hasAttempt = (question.attemptCount ?? 0) > 0;
  const scorePct =
    hasAttempt && question.bestScore != null
      ? Math.round((question.bestScore / question.maxMarks) * 100)
      : null;

  return (
    <div className="bg-white rounded-xl shadow-edu-sm hover:shadow-edu-md transition-default p-6">
      <div className="flex items-start gap-6">
        <div
          className={`w-16 h-16 rounded-xl flex items-center justify-center flex-shrink-0 ${
            isStruktur ? 'bg-[#DBEAFE]' : 'bg-[#EDE9FE]'
          }`}
        >
          <PencilLine
            className={`w-8 h-8 ${isStruktur ? 'text-[#1E3A8A]' : 'text-[#7C3AED]'}`}
          />
        </div>

        <div className="flex-1">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  isStruktur
                    ? 'bg-[#DBEAFE] text-[#1E3A8A]'
                    : 'bg-[#EDE9FE] text-[#7C3AED]'
                }`}
              >
                {isStruktur ? 'Soalan Struktur' : 'Soalan Esei'}
              </span>
              <span className="px-3 py-1 bg-[#F3F4F6] text-[#6B7280] rounded-full text-xs font-medium">
                [{question.maxMarks} markah]
              </span>
              <span className="px-3 py-1 bg-[#F3F4F6] text-[#6B7280] rounded-full text-xs font-medium">
                {question.subQuestion}
              </span>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <FormLevelBadge form={question.formLevel} />
              <DifficultyBadge difficulty={question.difficulty} />
            </div>
          </div>

          <p className="text-base font-medium text-[#111827] mb-4 leading-snug">
            {question.questionText}
          </p>

          <div className="flex items-center justify-between">
            <div>
              {hasAttempt && scorePct !== null && (
                <div className="flex items-center gap-2 text-sm">
                  <Award className="w-4 h-4 text-[#F59E0B]" />
                  <span className="text-[#6B7280]">Markah Terbaik:</span>
                  <span className="font-bold text-[#059669]">
                    {question.bestScore}/{question.maxMarks}
                  </span>
                  <span className="text-[#9CA3AF]">({scorePct}%)</span>
                </div>
              )}
            </div>
            <Button
              onClick={() => onNavigate('essay-writing', { questionId: String(question.questionId) })}
              className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              {hasAttempt ? 'Cuba Lagi' : 'Mula Latihan'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
