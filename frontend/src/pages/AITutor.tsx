import { useEffect, useRef, useState } from 'react';
import { Bot, Send, Square, Trash2, AlertTriangle, Sparkles } from 'lucide-react';
import { AppSidebar } from '../components/AppSidebar';
import { MarkdownMessage } from '../components/MarkdownMessage';
import { api, ChatMessage } from '../lib/api';

interface AITutorProps {
  onNavigate: (page: any, params?: any) => void;
}

const SUGGESTIONS = [
  'Siapakah Parameswara dan apakah sumbangan beliau?',
  'Jelaskan sebab-sebab pendudukan Jepun di Tanah Melayu.',
  'Apakah ciri-ciri utama Perlembagaan Persekutuan 1957?',
  'Mengapa Perikatan menang dalam Pilihan Raya 1955?',
  'Huraikan Dasar Ekonomi Baru (DEB) dan matlamatnya.',
  'Apakah yang dimaksudkan dengan Sistem Persekutuan?',
];

type SessionMessage = Omit<ChatMessage, 'conversationId' | 'sourcePageStart' | 'sourcePageEnd'>;

export function AITutor({ onNavigate }: AITutorProps) {
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  const chatScrollRef = useRef<HTMLDivElement>(null);
  const chatCtrlRef = useRef<AbortController | null>(null);
  const streamingRef = useRef<string>('');   // mirrors streamingText for abort handler
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    chatScrollRef.current?.scrollTo({ top: chatScrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, streamingText]);

  // Keep ref in sync so handleAbort can read current partial text
  useEffect(() => {
    streamingRef.current = streamingText ?? '';
  }, [streamingText]);

  const handleSend = (overrideText?: string) => {
    const question = (overrideText ?? chatInput).trim();
    if (!question || isSending) return;

    setChatInput('');
    setIsSending(true);
    setStreamingText('');
    streamingRef.current = '';

    const userMsg: SessionMessage = {
      messageId: -Date.now(),
      role: 'user',
      content: question,
      validationStatus: 'na',
      validationWarning: null,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    const history = messages.slice(-6).map((m) => ({
      role: m.role as 'user' | 'assistant',
      content: m.content,
    }));

    chatCtrlRef.current = api.sendGeneralTutorMessage(
      { question, history },
      {
        onToken: (chunk) => {
          setStreamingText((p) => {
            const next = (p ?? '') + chunk;
            streamingRef.current = next;
            return next;
          });
        },
        onReset: () => {
          setStreamingText('');
          streamingRef.current = '';
        },
        onFinal: (final) => {
          setMessages((prev) => [
            ...prev,
            {
              messageId: -Date.now() - 1,
              role: 'assistant',
              content: final.content,
              validationStatus: final.validationStatus,
              validationWarning: final.validationWarning,
              createdAt: new Date().toISOString(),
            },
          ]);
          setStreamingText(null);
          streamingRef.current = '';
          setIsSending(false);
          setTimeout(() => inputRef.current?.focus(), 50);
        },
        onError: (msg) => {
          setMessages((prev) => [
            ...prev,
            {
              messageId: -Date.now() - 2,
              role: 'assistant',
              content: `Maaf, terdapat ralat: ${msg}`,
              validationStatus: 'warned',
              validationWarning: msg,
              createdAt: new Date().toISOString(),
            },
          ]);
          setStreamingText(null);
          streamingRef.current = '';
          setIsSending(false);
        },
      },
    );
  };

  const handleAbort = () => {
    chatCtrlRef.current?.abort();
    const partial = streamingRef.current;
    if (partial.trim()) {
      setMessages((prev) => [
        ...prev,
        {
          messageId: -Date.now() - 1,
          role: 'assistant',
          content: partial,
          validationStatus: 'warned',
          validationWarning: 'Penjanaan dihentikan oleh pengguna.',
          createdAt: new Date().toISOString(),
        },
      ]);
    }
    setStreamingText(null);
    streamingRef.current = '';
    setIsSending(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleClear = () => {
    chatCtrlRef.current?.abort();
    setMessages([]);
    setStreamingText(null);
    streamingRef.current = '';
    setIsSending(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const isEmpty = messages.length === 0 && streamingText === null;

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="ai-tutor" onNavigate={onNavigate} />

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-5 flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-xl font-bold text-[#111827]">AI Tutor</h1>
            <p className="text-sm text-[#6B7280]">
              Tanya apa-apa sahaja tentang Sejarah KSSM Tingkatan 4 &amp; 5
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="flex items-center gap-2 px-3 py-2 text-sm text-[#DC2626] border border-[#FECACA] bg-[#FFF5F5] rounded-lg hover:bg-[#FEE2E2] transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Kosongkan
            </button>
          )}
        </div>

        {/* Chat area */}
        <div ref={chatScrollRef} className="flex-1 overflow-y-auto overflow-x-hidden">
          {isEmpty ? (
            <div className="max-w-2xl mx-auto px-6 py-12">
              <div className="text-center mb-10">
                <div className="w-16 h-16 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-edu-md">
                  <Bot className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-xl font-bold text-[#111827] mb-2">EduAI Tutor</h2>
                <p className="text-[#6B7280] text-sm leading-relaxed max-w-sm mx-auto">
                  Tanya sebarang soalan tentang Sejarah Malaysia — dari Bab 1 hingga Bab 10,
                  Tingkatan 4 dan 5. AI akan cari maklumat dari semua bab secara automatik.
                </p>
              </div>

              <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wide mb-3 text-center">
                Cadangan soalan
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSend(s)}
                    className="p-4 bg-white border border-[#E5E7EB] rounded-xl text-left text-sm text-[#374151] hover:border-[#1E3A8A] hover:bg-[#EFF6FF] hover:text-[#1E3A8A] transition-colors shadow-edu-sm"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-[#1E3A8A] mb-1.5" />
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-6 py-6 space-y-5">
              {messages.map((m) =>
                m.role === 'user' ? (
                  <div key={m.messageId} className="flex justify-end">
                    <div className="max-w-[72%] bg-[#1E3A8A] text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-edu-sm overflow-hidden">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap break-words w-full">{m.content}</p>
                    </div>
                  </div>
                ) : (
                  <div key={m.messageId} className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center flex-shrink-0 mt-0.5 shadow-edu-sm">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0 max-w-[78%]">
                      <div className="bg-white border border-[#E5E7EB] rounded-2xl rounded-tl-sm px-4 py-3 shadow-edu-sm overflow-hidden">
                        <MarkdownMessage content={m.content} />
                      </div>
                      {m.validationStatus === 'warned' && (
                        <div className="mt-1.5 flex items-start gap-1.5 px-1">
                          <AlertTriangle className="w-3 h-3 text-[#F59E0B] flex-shrink-0 mt-0.5" />
                          <p className="text-xs text-[#92400E] break-words">
                            {m.validationWarning ?? 'Jawapan ini belum disahkan sepenuhnya.'}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )
              )}

              {/* Streaming bubble */}
              {streamingText !== null && (
                <div className="flex gap-3">
                  <div className={`w-8 h-8 rounded-full bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center flex-shrink-0 mt-0.5 shadow-edu-sm ${streamingText === '' ? 'animate-pulse' : ''}`}>
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-white border border-[#E5E7EB] rounded-2xl rounded-tl-sm px-4 py-3 shadow-edu-sm max-w-[78%] overflow-hidden min-w-[80px]">
                    {streamingText === '' ? (
                      /* Typing dots — shown while waiting for first token */
                      <div className="flex items-center gap-1 h-5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#9CA3AF] animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-[#9CA3AF] animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-[#9CA3AF] animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    ) : (
                      <>
                        <MarkdownMessage content={streamingText} />
                        <span className="inline-block w-0.5 h-4 bg-[#1E3A8A] ml-0.5 animate-pulse align-bottom" />
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input bar */}
        <div className="bg-white border-t border-[#E5E7EB] px-6 py-4 flex-shrink-0">
          <div className="max-w-3xl mx-auto">
            <div className="flex gap-3 items-end border border-[#E5E7EB] rounded-xl px-4 py-3 bg-[#F9FAFB] focus-within:border-[#1E3A8A] focus-within:bg-white transition-colors shadow-edu-sm">
              <textarea
                ref={inputRef}
                value={chatInput}
                onChange={(e) => {
                  setChatInput(e.target.value);
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px';
                }}
                onKeyDown={handleKeyDown}
                placeholder="Tanya apa-apa tentang Sejarah Tingkatan 4 & 5…"
                disabled={isSending}
                rows={1}
                className="flex-1 min-w-0 bg-transparent text-sm text-[#111827] placeholder-[#9CA3AF] resize-none focus:outline-none disabled:opacity-50 leading-relaxed"
                style={{ maxHeight: '140px' }}
              />
              {isSending ? (
                /* Stop button — aborts stream and preserves partial response */
                <button
                  onClick={handleAbort}
                  className="w-9 h-9 bg-[#DC2626] rounded-xl flex items-center justify-center flex-shrink-0 hover:bg-[#B91C1C] transition-colors"
                  title="Hentikan penjanaan"
                >
                  <Square className="w-3.5 h-3.5 text-white fill-white" />
                </button>
              ) : (
                <button
                  onClick={() => handleSend()}
                  disabled={!chatInput.trim()}
                  className="w-9 h-9 bg-[#1E3A8A] rounded-xl flex items-center justify-center flex-shrink-0 hover:bg-[#1E40AF] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-4 h-4 text-white" />
                </button>
              )}
            </div>
            <p className="text-xs text-[#9CA3AF] mt-2 text-center">
              AI mencari maklumat daripada semua bab Sejarah KSSM · Enter untuk hantar
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
