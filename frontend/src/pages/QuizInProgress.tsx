import { useState, useEffect } from 'react';
import { ArrowLeft, Clock, Flag, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';

interface QuizInProgressProps {
  onNavigate: (page: any, params?: any) => void;
  quizId: string | null;
}

const questions = [
  {
    id: 1,
    question: 'Apakah nama penuh Raja pertama Kesultanan Melayu Melaka?',
    options: [
      'Parameswara',
      'Sultan Muhammad Shah',
      'Sultan Mansur Shah',
      'Sultan Mahmud Shah',
    ],
    correctAnswer: 0,
  },
  {
    id: 2,
    question: 'Pada tahun berapakah Melaka jatuh ke tangan Portugis?',
    options: ['1400', '1511', '1641', '1786'],
    correctAnswer: 1,
  },
  {
    id: 3,
    question: 'Apakah sistem pentadbiran tertinggi di Kesultanan Melayu Melaka?',
    options: ['Bendahara', 'Temenggung', 'Sultan', 'Laksamana'],
    correctAnswer: 2,
  },
];

export function QuizInProgress({ onNavigate, quizId }: QuizInProgressProps) {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<(number | null)[]>(Array(questions.length).fill(null));
  const [flagged, setFlagged] = useState<Set<number>>(new Set());
  const [timeRemaining, setTimeRemaining] = useState(10 * 60); // 10 minutes

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleAnswer = (optionIndex: number) => {
    const newAnswers = [...answers];
    newAnswers[currentQuestion] = optionIndex;
    setAnswers(newAnswers);
  };

  const toggleFlag = () => {
    const newFlagged = new Set(flagged);
    if (newFlagged.has(currentQuestion)) {
      newFlagged.delete(currentQuestion);
    } else {
      newFlagged.add(currentQuestion);
    }
    setFlagged(newFlagged);
  };

  const handleSubmit = () => {
    onNavigate('quiz-results', { quizId });
  };

  const answeredCount = answers.filter((a) => a !== null).length;
  const progress = (currentQuestion + 1) / questions.length * 100;

  return (
    <div className="min-h-screen bg-[#F9FAFB]">
      {/* Header Bar */}
      <div className="bg-white border-b border-[#E5E7EB] px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to exit? Your progress will be lost.')) {
                  onNavigate('quiz-selection');
                }
              }}
              className="p-2 hover:bg-[#F3F4F6] rounded transition-default"
            >
              <ArrowLeft className="w-5 h-5 text-[#6B7280]" />
            </button>
            <div>
              <h2 className="font-bold text-[#111827]">Kesultanan Melayu Melaka Quiz</h2>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 text-[#F59E0B]">
              <Clock className="w-5 h-5" />
              <span className="font-bold">{formatTime(timeRemaining)}</span>
            </div>
            <div className="text-sm text-[#6B7280]">
              Question <span className="font-bold text-[#111827]">{currentQuestion + 1}</span> of{' '}
              {questions.length}
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white border-b border-[#E5E7EB] px-6 py-3">
        <div className="max-w-4xl mx-auto">
          <Progress value={progress} className="h-2" />
        </div>
      </div>

      {/* Question Area */}
      <div className="p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow-edu-md p-8 mb-6">
            <div className="flex items-center justify-between mb-6">
              <span className="px-3 py-1 bg-[#DBEAFE] text-[#1E3A8A] text-sm font-medium rounded-full">
                Question {currentQuestion + 1}
              </span>
              <button
                onClick={toggleFlag}
                className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium transition-default ${
                  flagged.has(currentQuestion)
                    ? 'bg-[#FEF3C7] text-[#F59E0B]'
                    : 'bg-[#F3F4F6] text-[#6B7280] hover:bg-[#E5E7EB]'
                }`}
              >
                <Flag className="w-4 h-4" />
                {flagged.has(currentQuestion) ? 'Flagged' : 'Flag for Review'}
              </button>
            </div>

            <h3 className="text-xl font-bold text-[#111827] mb-6">
              {questions[currentQuestion].question}
            </h3>

            <div className="space-y-3">
              {questions[currentQuestion].options.map((option, index) => (
                <button
                  key={index}
                  onClick={() => handleAnswer(index)}
                  className={`w-full flex items-center gap-4 p-4 rounded-lg border-2 transition-default text-left ${
                    answers[currentQuestion] === index
                      ? 'border-[#1E3A8A] bg-[#EFF6FF]'
                      : 'border-[#E5E7EB] hover:border-[#D1D5DB] hover:bg-[#F9FAFB]'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 font-bold ${
                      answers[currentQuestion] === index
                        ? 'bg-[#1E3A8A] text-white'
                        : 'bg-[#F3F4F6] text-[#6B7280]'
                    }`}
                  >
                    {String.fromCharCode(65 + index)}
                  </div>
                  <span className="text-[#111827]">{option}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <Button
              onClick={() => setCurrentQuestion(Math.max(0, currentQuestion - 1))}
              disabled={currentQuestion === 0}
              variant="outline"
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              Previous
            </Button>

            {/* Question Navigator */}
            <div className="flex items-center gap-2">
              {questions.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentQuestion(idx)}
                  className={`w-10 h-10 rounded-lg font-medium text-sm transition-default ${
                    idx === currentQuestion
                      ? 'bg-[#1E3A8A] text-white ring-2 ring-[#1E3A8A] ring-offset-2'
                      : answers[idx] !== null
                      ? 'bg-[#DBEAFE] text-[#1E3A8A]'
                      : 'bg-[#F3F4F6] text-[#6B7280] hover:bg-[#E5E7EB]'
                  } ${flagged.has(idx) ? 'relative' : ''}`}
                >
                  {idx + 1}
                  {flagged.has(idx) && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-[#F59E0B] rounded-full" />
                  )}
                </button>
              ))}
            </div>

            {currentQuestion === questions.length - 1 ? (
              <Button
                onClick={handleSubmit}
                className="bg-[#059669] hover:bg-[#047857] text-white"
              >
                Submit Quiz
              </Button>
            ) : (
              <Button
                onClick={() => setCurrentQuestion(Math.min(questions.length - 1, currentQuestion + 1))}
                className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
              >
                Next
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>

          {/* Summary */}
          <div className="mt-6 bg-white rounded-xl p-4 shadow-edu-sm">
            <div className="flex items-center justify-center gap-8 text-sm">
              <div>
                <span className="text-[#6B7280]">Answered: </span>
                <span className="font-bold text-[#111827]">{answeredCount}/{questions.length}</span>
              </div>
              <div>
                <span className="text-[#6B7280]">Flagged: </span>
                <span className="font-bold text-[#F59E0B]">{flagged.size}</span>
              </div>
              <div>
                <span className="text-[#6B7280]">Remaining: </span>
                <span className="font-bold text-[#DC2626]">{questions.length - answeredCount}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
