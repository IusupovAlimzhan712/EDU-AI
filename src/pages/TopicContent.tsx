import { useState } from 'react';
import { ArrowLeft, Bookmark, BookmarkCheck, Check, ChevronLeft, ChevronRight, X, ZoomIn, ZoomOut, Maximize2, Download, Send, Bot } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { ChatBubble } from '../components/ChatBubble';

interface TopicContentProps {
  onNavigate: (page: any) => void;
  topicId: string | null;
}

export function TopicContent({ onNavigate, topicId }: TopicContentProps) {
  const [showSyllabus, setShowSyllabus] = useState(true);
  const [showChat, setShowChat] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatMessages, setChatMessages] = useState([
    {
      type: 'ai' as const,
      message: 'Selamat datang! Saya boleh membantu anda memahami topik ini. Apa yang anda ingin tanya?',
      timestamp: '10:30 AM',
    },
  ]);

  const totalPages = 15;
  const topics = [
    { id: 1, title: 'Pengenalan Tamadun Islam', completed: true },
    { id: 2, title: 'Hijrah ke Madinah', completed: true },
    { id: 3, title: 'Piagam Madinah', completed: false },
    { id: 4, title: 'Pembinaan Masjid Nabawi', completed: false },
    { id: 5, title: 'Perkembangan Ekonomi', completed: false },
  ];

  const suggestedQuestions = [
    'Explain this concept',
    'What are the key dates?',
    'Why is this important for SPM?',
    'Summarize this page',
  ];

  const handleSendMessage = () => {
    if (!chatMessage.trim()) return;

    const newMessages = [
      ...chatMessages,
      {
        type: 'user' as const,
        message: chatMessage,
        timestamp: new Date().toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' }),
      },
    ];

    setChatMessages(newMessages);
    setChatMessage('');

    // Simulate AI response
    setTimeout(() => {
      setChatMessages([
        ...newMessages,
        {
          type: 'ai' as const,
          message: 'Berdasarkan sukatan KSSM, konsep ini merujuk kepada pembentukan masyarakat Islam yang berpaksikan Piagam Madinah. Ini adalah perkara penting untuk SPM kerana ia menunjukkan asas perpaduan kaum di Madinah.',
          timestamp: new Date().toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }, 1000);
  };

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      {/* Left Panel - Syllabus Sidebar */}
      {showSyllabus && (
        <div className="w-[280px] bg-white border-r border-[#E5E7EB] flex flex-col">
          <div className="p-4 border-b border-[#E5E7EB] flex items-center justify-between">
            <h3 className="font-bold text-[#111827]">Bab 5</h3>
            <button
              onClick={() => setShowSyllabus(false)}
              className="p-1 hover:bg-[#F3F4F6] rounded transition-default"
            >
              <ChevronLeft className="w-5 h-5 text-[#6B7280]" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <h4 className="text-sm font-medium text-[#6B7280] mb-3">Topics</h4>
            {topics.map((topic) => (
              <button
                key={topic.id}
                className={`w-full flex items-center gap-3 p-3 rounded-lg mb-2 transition-default text-left ${
                  topic.id === 2
                    ? 'bg-[#EFF6FF] text-[#1E3A8A]'
                    : 'text-[#374151] hover:bg-[#F3F4F6]'
                }`}
              >
                <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                  topic.completed ? 'bg-[#059669]' : 'border-2 border-[#D1D5DB]'
                }`}>
                  {topic.completed && <Check className="w-3 h-3 text-white" />}
                </div>
                <span className="text-sm">{topic.title}</span>
              </button>
            ))}
          </div>

          <div className="p-4 border-t border-[#E5E7EB]">
            <div className="text-xs text-[#6B7280]">
              Progress: {topics.filter(t => t.completed).length}/{topics.length} completed
            </div>
            <div className="mt-2 h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#059669] rounded-full transition-all"
                style={{ width: `${(topics.filter(t => t.completed).length / topics.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Center Panel - PDF Viewer */}
      <div className="flex-1 flex flex-col bg-white">
        {/* Top Bar */}
        <div className="h-16 border-b border-[#E5E7EB] px-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => onNavigate('topics')}
              className="p-2 hover:bg-[#F3F4F6] rounded transition-default"
            >
              <ArrowLeft className="w-5 h-5 text-[#6B7280]" />
            </button>
            {!showSyllabus && (
              <button
                onClick={() => setShowSyllabus(true)}
                className="p-2 hover:bg-[#F3F4F6] rounded transition-default"
              >
                <ChevronRight className="w-5 h-5 text-[#6B7280]" />
              </button>
            )}
            <div>
              <h2 className="font-bold text-[#111827]">Kerajaan Islam di Madinah</h2>
              <p className="text-sm text-[#6B7280]">Bab 5 - Form 4</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsBookmarked(!isBookmarked)}
              className="p-2 hover:bg-[#F3F4F6] rounded transition-default"
            >
              {isBookmarked ? (
                <BookmarkCheck className="w-5 h-5 text-[#F59E0B]" fill="#F59E0B" />
              ) : (
                <Bookmark className="w-5 h-5 text-[#6B7280]" />
              )}
            </button>
            <Button className="bg-[#059669] hover:bg-[#047857] text-white">
              <Check className="w-4 h-4 mr-2" />
              Mark as Complete
            </Button>
          </div>
        </div>

        {/* PDF Viewer Area */}
        <div className="flex-1 overflow-auto bg-[#F3F4F6] flex items-center justify-center p-8">
          <div
            className="bg-white shadow-edu-lg"
            style={{ width: `${zoom}%`, maxWidth: '900px' }}
          >
            {/* Mock PDF Content */}
            <div className="p-12 space-y-4">
              <h1 className="text-3xl font-bold text-center mb-6">Hijrah ke Madinah</h1>
              <p className="text-justify leading-relaxed">
                Hijrah Nabi Muhammad SAW dari Makkah ke Madinah pada tahun 622 Masihi merupakan peristiwa penting dalam sejarah Islam. Perpindahan ini bukan sahaja menyelamatkan umat Islam dari penganiayaan kaum Quraisy, tetapi juga membuka lembaran baru dalam perkembangan agama Islam.
              </p>
              <p className="text-justify leading-relaxed">
                Madinah menyediakan suasana yang lebih kondusif untuk perkembangan Islam. Di sini, Nabi Muhammad SAW dapat membina sebuah masyarakat Islam yang teratur dan berpaksikan kepada prinsip-prinsip Islam.
              </p>
              <h2 className="text-xl font-bold mt-6 mb-3">Sebab-sebab Hijrah</h2>
              <ul className="list-disc pl-8 space-y-2">
                <li>Penganiayaan yang semakin meningkat terhadap umat Islam di Makkah</li>
                <li>Jemputan penduduk Madinah untuk Nabi Muhammad SAW berhijrah</li>
                <li>Keperluan untuk membina masyarakat Islam yang kukuh</li>
                <li>Strategi penyebaran Islam yang lebih berkesan</li>
              </ul>
              <h2 className="text-xl font-bold mt-6 mb-3">Impak Hijrah</h2>
              <p className="text-justify leading-relaxed">
                Hijrah membawa perubahan besar dalam sejarah Islam. Ia menandakan permulaan kalendar Hijrah dan menjadi asas kepada pembentukan negara Islam pertama di Madinah.
              </p>
            </div>
          </div>
        </div>

        {/* PDF Controls Bar */}
        <div className="h-14 border-t border-[#E5E7EB] px-6 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="p-2 hover:bg-[#F3F4F6] rounded transition-default disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-[#6B7280] px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="p-2 hover:bg-[#F3F4F6] rounded transition-default disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setZoom(Math.max(50, zoom - 25))}
              className="p-2 hover:bg-[#F3F4F6] rounded transition-default"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <select
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="px-2 py-1 border border-[#D1D5DB] rounded text-sm"
            >
              <option value="50">50%</option>
              <option value="75">75%</option>
              <option value="100">100%</option>
              <option value="125">125%</option>
              <option value="150">150%</option>
            </select>
            <button
              onClick={() => setZoom(Math.min(150, zoom + 25))}
              className="p-2 hover:bg-[#F3F4F6] rounded transition-default"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <div className="w-px h-6 bg-[#D1D5DB] mx-2" />
            <button className="p-2 hover:bg-[#F3F4F6] rounded transition-default">
              <Maximize2 className="w-4 h-4" />
            </button>
            <button className="p-2 hover:bg-[#F3F4F6] rounded transition-default">
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel - AI Chat */}
      {showChat && (
        <div className="w-[320px] bg-white border-l border-[#E5E7EB] flex flex-col">
          {/* Chat Header */}
          <div className="h-16 border-b border-[#E5E7EB] px-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#DBEAFE] rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-[#1E3A8A]" />
              </div>
              <div>
                <h3 className="font-bold text-[#111827] text-sm">AI Tutor</h3>
                <p className="text-xs text-[#059669]">Online - Ready to help</p>
              </div>
            </div>
            <button
              onClick={() => setShowChat(false)}
              className="p-1 hover:bg-[#F3F4F6] rounded transition-default"
            >
              <X className="w-5 h-5 text-[#6B7280]" />
            </button>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4">
            {chatMessages.map((msg, idx) => (
              <ChatBubble key={idx} {...msg} />
            ))}
          </div>

          {/* Suggested Questions */}
          <div className="px-4 pb-2">
            <div className="flex gap-2 overflow-x-auto pb-2">
              {suggestedQuestions.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => setChatMessage(question)}
                  className="flex-shrink-0 px-3 py-1.5 bg-[#F3F4F6] hover:bg-[#E5E7EB] rounded-full text-xs text-[#374151] transition-default"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>

          {/* Chat Input */}
          <div className="border-t border-[#E5E7EB] p-4">
            <div className="flex gap-2">
              <Textarea
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask about this topic..."
                className="resize-none min-h-[80px]"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!chatMessage.trim()}
                className="bg-[#1E3A8A] hover:bg-[#1E40AF] h-auto"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Toggle Chat Button (when hidden) */}
      {!showChat && (
        <button
          onClick={() => setShowChat(true)}
          className="fixed right-4 bottom-4 w-14 h-14 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white rounded-full shadow-edu-lg flex items-center justify-center transition-default"
        >
          <Bot className="w-6 h-6" />
        </button>
      )}
    </div>
  );
}
