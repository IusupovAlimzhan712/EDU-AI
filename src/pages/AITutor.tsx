import { useState } from 'react';
import { Bot, Send, Plus, Clock, Trash2 } from 'lucide-react';
import { AppSidebar } from '../components/AppSidebar';
import { ChatBubble } from '../components/ChatBubble';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';

interface AITutorProps {
  onNavigate: (page: any) => void;
}

const suggestedTopics = [
  'Explain Kesultanan Melayu Melaka',
  'What caused World War 2 effects on Malaya?',
  'Key dates for Form 4 Bab 3',
  'How to answer HOTS questions?',
];

const conversationHistory = [
  { id: '1', title: 'Tamadun Islam di Madinah', date: 'Today', time: '2:30 PM' },
  { id: '2', title: 'Pendudukan Jepun', date: 'Yesterday', time: '4:15 PM' },
  { id: '3', title: 'Kemerdekaan Tanah Melayu', date: 'This Week', time: 'Mon 3:20 PM' },
  { id: '4', title: 'Pembentukan Malaysia', date: 'This Week', time: 'Sun 11:30 AM' },
];

export function AITutor({ onNavigate }: AITutorProps) {
  const [showHistory, setShowHistory] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{
    type: 'user' | 'ai';
    message: string;
    timestamp: string;
  }>>([
    {
      type: 'ai',
      message: 'Selamat datang! Saya EduAI, pembantu kajian Sejarah anda. Saya boleh membantu anda memahami topik-topik dalam sukatan KSSM Sejarah Tingkatan 4 dan 5. Apa yang anda ingin pelajari hari ini?',
      timestamp: '10:00 AM',
    },
  ]);

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
          message: 'Berdasarkan sukatan KSSM Sejarah, saya akan jelaskan topik ini dengan lebih terperinci. **Kesultanan Melayu Melaka** diasaskan pada abad ke-15 oleh Parameswara. Ia merupakan salah satu kerajaan paling penting dalam sejarah Alam Melayu. Tarikh penting: 1400 - Penubuhan Melaka, 1511 - Kejatuhan Melaka kepada Portugis.',
          timestamp: new Date().toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    }, 1000);
  };

  const handleSuggestedTopic = (topic: string) => {
    setChatMessage(topic);
  };

  const handleNewChat = () => {
    setChatMessages([
      {
        type: 'ai',
        message: 'Selamat datang! Saya EduAI, pembantu kajian Sejarah anda. Saya boleh membantu anda memahami topik-topik dalam sukatan KSSM Sejarah Tingkatan 4 dan 5. Apa yang anda ingin pelajari hari ini?',
        timestamp: new Date().toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="ai-tutor" onNavigate={onNavigate} />

      {/* Conversation History Sidebar */}
      {showHistory && (
        <div className="w-[280px] bg-white border-r border-[#E5E7EB] flex flex-col">
          <div className="p-4 border-b border-[#E5E7EB]">
            <h3 className="font-bold text-[#111827] mb-2">Conversation History</h3>
            <Button
              onClick={handleNewChat}
              className="w-full bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Chat
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            {conversationHistory.map((conv) => (
              <div
                key={conv.id}
                className="p-3 rounded-lg hover:bg-[#F3F4F6] cursor-pointer mb-2 group"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[#111827] mb-1 line-clamp-1">
                      {conv.title}
                    </p>
                    <p className="text-xs text-[#6B7280] flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {conv.time}
                    </p>
                  </div>
                  <button className="opacity-0 group-hover:opacity-100 p-1 hover:bg-[#FEE2E2] rounded transition-default">
                    <Trash2 className="w-4 h-4 text-[#DC2626]" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="h-16 bg-white border-b border-[#E5E7EB] px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-full flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-[#111827]">AI Tutor</h2>
              <p className="text-sm text-[#059669]">Online - Ready to help</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={() => setShowHistory(!showHistory)}
              variant="outline"
            >
              {showHistory ? 'Hide' : 'Show'} History
            </Button>
            <Button
              onClick={handleNewChat}
              className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Chat
            </Button>
          </div>
        </div>

        {/* Chat Messages Area */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto">
            {chatMessages.length === 1 ? (
              <div className="text-center py-12">
                <div className="w-20 h-20 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-full flex items-center justify-center mx-auto mb-6">
                  <Bot className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-[#111827] mb-4">
                  Welcome to AI Tutor
                </h2>
                <p className="text-[#6B7280] mb-8">
                  Ask me anything about KSSM Sejarah Form 4 & 5
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                  {suggestedTopics.map((topic, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSuggestedTopic(topic)}
                      className="bg-white border border-[#E5E7EB] rounded-xl p-4 hover:shadow-edu-md hover:border-[#1E3A8A] transition-default text-left"
                    >
                      <p className="text-sm font-medium text-[#111827]">{topic}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                {chatMessages.map((msg, idx) => (
                  <ChatBubble key={idx} {...msg} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Chat Input Area */}
        <div className="bg-white border-t border-[#E5E7EB] p-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <Textarea
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask about KSSM Sejarah topics..."
                className="resize-none min-h-[100px]"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!chatMessage.trim()}
                className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white h-auto px-6"
              >
                <Send className="w-5 h-5" />
              </Button>
            </div>
            <p className="text-xs text-[#6B7280] mt-3 text-center">
              Responses are based on KSSM Sejarah syllabus
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
