import { useState, useEffect } from 'react';
import { ArrowLeft, Save, Send, HelpCircle, Clock } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';

interface EssayWritingProps {
  onNavigate: (page: any, params?: any) => void;
  essayId: string | null;
}

export function EssayWriting({ onNavigate, essayId }: EssayWritingProps) {
  const [essay, setEssay] = useState('');
  const [wordCount, setWordCount] = useState(0);
  const [timeSpent, setTimeSpent] = useState(0);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeSpent((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const words = essay.trim().split(/\s+/).filter((w) => w.length > 0);
    setWordCount(words.length);
  }, [essay]);

  const handleSave = () => {
    setLastSaved(new Date());
  };

  const handleSubmit = () => {
    if (window.confirm('Are you sure you want to submit your essay for evaluation?')) {
      onNavigate('essay-feedback', { essayId });
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="h-screen bg-[#F9FAFB] flex">
      {/* Left Panel - Question */}
      <div className="w-[40%] bg-white border-r border-[#E5E7EB] flex flex-col">
        <div className="p-6 border-b border-[#E5E7EB]">
          <button
            onClick={() => onNavigate('essay-practice')}
            className="flex items-center gap-2 text-[#6B7280] hover:text-[#374151] mb-4 transition-default"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Back to Essay Practice</span>
          </button>

          <div className="flex items-center gap-2 mb-3">
            <span className="px-3 py-1 bg-[#DBEAFE] text-[#1E3A8A] rounded-full text-xs font-medium">
              Soalan Struktur
            </span>
            <span className="px-3 py-1 bg-[#F3F4F6] text-[#6B7280] rounded-full text-xs font-medium">
              [10 marks]
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <h2 className="text-xl font-bold text-[#111827] mb-4">
            Huraikan faktor-faktor kejatuhan Kesultanan Melayu Melaka.
          </h2>

          <div className="bg-[#FEF3C7] border-l-4 border-[#F59E0B] p-4 rounded mb-6">
            <h3 className="font-bold text-[#111827] mb-2">Key Instructions:</h3>
            <ul className="text-sm text-[#374151] space-y-1 list-disc pl-5">
              <li>Answer in Bahasa Malaysia</li>
              <li>Provide at least 5 factors</li>
              <li>Include specific dates and events</li>
              <li>Use historical evidence to support your points</li>
            </ul>
          </div>

          <div className="mb-6">
            <h3 className="font-bold text-[#111827] mb-2">Marking Criteria:</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[#6B7280]">Content Accuracy</span>
                <span className="font-medium">4 marks</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#6B7280]">Analysis & Understanding</span>
                <span className="font-medium">3 marks</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#6B7280]">Structure & Organization</span>
                <span className="font-medium">2 marks</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#6B7280]">Language</span>
                <span className="font-medium">1 mark</span>
              </div>
            </div>
          </div>

          <Button
            onClick={() => onNavigate('ai-tutor')}
            variant="outline"
            className="w-full"
          >
            <HelpCircle className="w-4 h-4 mr-2" />
            Ask AI for Hints
          </Button>
        </div>
      </div>

      {/* Right Panel - Writing Area */}
      <div className="flex-1 flex flex-col">
        <div className="bg-white border-b border-[#E5E7EB] p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-[#111827]">Your Response</h3>
            <div className="flex items-center gap-4 text-sm text-[#6B7280]">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>Time: {formatTime(timeSpent)}</span>
              </div>
              {lastSaved && (
                <span className="text-[#059669]">
                  Saved at {lastSaved.toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm">
              <span className="text-[#6B7280]">Word count: </span>
              <span className={`font-bold ${
                wordCount >= 300 && wordCount <= 500
                  ? 'text-[#059669]'
                  : wordCount > 500
                  ? 'text-[#F59E0B]'
                  : 'text-[#6B7280]'
              }`}>
                {wordCount}
              </span>
              <span className="text-[#6B7280]"> / recommended 300-500 words</span>
            </div>
          </div>
        </div>

        <div className="flex-1 p-6">
          <Textarea
            value={essay}
            onChange={(e) => setEssay(e.target.value)}
            placeholder="Start writing your essay here..."
            className="w-full h-full resize-none text-base leading-relaxed"
          />
        </div>

        <div className="bg-white border-t border-[#E5E7EB] p-6">
          <div className="flex justify-between items-center">
            <Button
              onClick={handleSave}
              variant="outline"
            >
              <Save className="w-4 h-4 mr-2" />
              Save Draft
            </Button>

            <Button
              onClick={handleSubmit}
              disabled={wordCount < 50}
              className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              <Send className="w-4 h-4 mr-2" />
              Submit for Evaluation
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
