import { Bot, User } from 'lucide-react';

interface ChatBubbleProps {
  type: 'user' | 'ai';
  message: string;
  timestamp?: string;
  className?: string;
}

export function ChatBubble({ type, message, timestamp, className = '' }: ChatBubbleProps) {
  if (type === 'user') {
    return (
      <div className={`flex justify-end mb-4 ${className}`}>
        <div className="max-w-[80%]">
          <div className="bg-[#1E3A8A] text-white rounded-2xl rounded-tr-md px-4 py-3">
            <p className="text-sm leading-relaxed">{message}</p>
          </div>
          {timestamp && (
            <p className="text-xs text-[#6B7280] mt-1 text-right">{timestamp}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex justify-start mb-4 ${className}`}>
      <div className="flex gap-2 max-w-[80%]">
        <div className="w-8 h-8 rounded-full bg-[#DBEAFE] flex items-center justify-center flex-shrink-0 mt-1">
          <Bot className="w-5 h-5 text-[#1E3A8A]" />
        </div>
        <div>
          <div className="bg-white border border-[#E5E7EB] rounded-2xl rounded-tl-md px-4 py-3">
            <p className="text-sm leading-relaxed text-[#111827]">{message}</p>
          </div>
          {timestamp && (
            <p className="text-xs text-[#6B7280] mt-1">{timestamp}</p>
          )}
        </div>
      </div>
    </div>
  );
}
