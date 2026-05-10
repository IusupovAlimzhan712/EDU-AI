import { AppSidebar } from '../components/AppSidebar';
import { CircularProgress } from '../components/CircularProgress';
import { Button } from '../components/ui/button';
import { Check, X, ChevronDown, ChevronUp, MessageSquare } from 'lucide-react';
import { useState } from 'react';

interface QuizResultsProps {
  onNavigate: (page: any, params?: any) => void;
  quizId: string | null;
}

const results = {
  score: 8,
  total: 10,
  percentage: 80,
  timeTaken: '8:45',
  correctAnswers: 8,
  incorrectAnswers: 2,
};

const questions = [
  {
    id: 1,
    question: 'Apakah nama penuh Raja pertama Kesultanan Melayu Melaka?',
    userAnswer: 'Parameswara',
    correctAnswer: 'Parameswara',
    isCorrect: true,
    explanation: 'Parameswara adalah pengasas Kesultanan Melayu Melaka pada tahun 1400.',
  },
  {
    id: 2,
    question: 'Pada tahun berapakah Melaka jatuh ke tangan Portugis?',
    userAnswer: '1400',
    correctAnswer: '1511',
    isCorrect: false,
    explanation: 'Melaka jatuh ke tangan Portugis pada tahun 1511 selepas Alfonso de Albuquerque menyerang kota tersebut.',
  },
  {
    id: 3,
    question: 'Apakah sistem pentadbiran tertinggi di Kesultanan Melayu Melaka?',
    userAnswer: 'Sultan',
    correctAnswer: 'Sultan',
    isCorrect: true,
    explanation: 'Sultan adalah pemerintah tertinggi dalam sistem pentadbiran Kesultanan Melayu Melaka.',
  },
];

export function QuizResults({ onNavigate, quizId }: QuizResultsProps) {
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set());
  const [showOnlyIncorrect, setShowOnlyIncorrect] = useState(false);

  const toggleQuestion = (id: number) => {
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedQuestions(newExpanded);
  };

  const filteredQuestions = showOnlyIncorrect
    ? questions.filter((q) => !q.isCorrect)
    : questions;

  const performanceMessage =
    results.percentage >= 90
      ? 'Excellent! 🎉'
      : results.percentage >= 70
      ? 'Good job! 👍'
      : results.percentage >= 50
      ? 'Keep practicing! 💪'
      : "Don't give up! 📚";

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="quiz-selection" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827]">Quiz Results</h1>
          <p className="text-[#6B7280]">Kesultanan Melayu Melaka</p>
        </div>

        {/* Main Content */}
        <div className="p-8 max-w-4xl mx-auto">
          {/* Results Header Card */}
          <div className="bg-white rounded-xl shadow-edu-md p-8 mb-8 text-center">
            <CircularProgress percentage={results.percentage} size="large" />

            <h2 className="text-3xl font-bold text-[#111827] mt-6 mb-2">
              {results.score}/{results.total}
            </h2>
            <p className="text-xl text-[#6B7280] mb-4">{results.percentage}%</p>
            <p className="text-2xl font-bold text-[#1E3A8A] mb-4">{performanceMessage}</p>
            <p className="text-sm text-[#6B7280]">
              Completed in {results.timeTaken} • {new Date().toLocaleDateString()}
            </p>
          </div>

          {/* Score Breakdown */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-8">
            <h3 className="font-bold text-[#111827] mb-4">Score Breakdown</h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="text-[#6B7280]">Correct Answers</span>
                  <span className="font-medium text-[#059669]">{results.correctAnswers}</span>
                </div>
                <div className="h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#059669] rounded-full"
                    style={{ width: `${(results.correctAnswers / results.total) * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="text-[#6B7280]">Incorrect Answers</span>
                  <span className="font-medium text-[#DC2626]">{results.incorrectAnswers}</span>
                </div>
                <div className="h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#DC2626] rounded-full"
                    style={{ width: `${(results.incorrectAnswers / results.total) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4 mb-8">
            <Button
              onClick={() => setShowOnlyIncorrect(!showOnlyIncorrect)}
              variant="outline"
              className="flex-1"
            >
              {showOnlyIncorrect ? 'Show All' : 'Show Incorrect Only'}
            </Button>
            <Button
              onClick={() => onNavigate('quiz-in-progress', { quizId })}
              variant="outline"
              className="flex-1"
            >
              Retry Quiz
            </Button>
            <Button
              onClick={() => onNavigate('quiz-selection')}
              className="flex-1 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              Back to Quizzes
            </Button>
          </div>

          {/* Review Answers */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6">
            <h3 className="font-bold text-[#111827] mb-4">Review Answers</h3>

            <div className="space-y-4">
              {filteredQuestions.map((q) => (
                <div
                  key={q.id}
                  className={`border-2 rounded-lg overflow-hidden ${
                    q.isCorrect ? 'border-[#D1FAE5]' : 'border-[#FEE2E2]'
                  }`}
                >
                  <div
                    className={`p-4 ${q.isCorrect ? 'bg-[#D1FAE5]/30' : 'bg-[#FEE2E2]/30'}`}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          q.isCorrect ? 'bg-[#059669]' : 'bg-[#DC2626]'
                        }`}
                      >
                        {q.isCorrect ? (
                          <Check className="w-5 h-5 text-white" />
                        ) : (
                          <X className="w-5 h-5 text-white" />
                        )}
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-[#111827] mb-3">{q.question}</p>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-[#6B7280]">Your answer: </span>
                            <span
                              className={`font-medium ${
                                q.isCorrect ? 'text-[#059669]' : 'text-[#DC2626]'
                              }`}
                            >
                              {q.userAnswer}
                            </span>
                          </div>
                          {!q.isCorrect && (
                            <div>
                              <span className="text-[#6B7280]">Correct answer: </span>
                              <span className="font-medium text-[#059669]">
                                {q.correctAnswer}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => toggleQuestion(q.id)}
                        className="p-2 hover:bg-white/50 rounded transition-default"
                      >
                        {expandedQuestions.has(q.id) ? (
                          <ChevronUp className="w-5 h-5 text-[#6B7280]" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-[#6B7280]" />
                        )}
                      </button>
                    </div>

                    {expandedQuestions.has(q.id) && (
                      <div className="mt-4 pt-4 border-t border-white/50">
                        <p className="text-sm text-[#374151] mb-3">{q.explanation}</p>
                        <Button
                          onClick={() => onNavigate('ai-tutor')}
                          variant="outline"
                          size="sm"
                        >
                          <MessageSquare className="w-4 h-4 mr-2" />
                          Ask AI Tutor
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
