import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft, Bookmark, BookmarkCheck, Check, ChevronLeft, ChevronRight,
  X, ZoomIn, ZoomOut, Bot, FileWarning, Send, Square, Trash2, AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { Button } from '../components/ui/button';
import { MarkdownMessage } from '../components/MarkdownMessage';
import { api, TopicDetail, TopicSummary, ChatMessage, APIError } from '../lib/api';

pdfjs.GlobalWorkerOptions.workerSrc =
  `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

interface TopicContentProps {
  onNavigate: (page: any, params?: any) => void;
  topicId: string | null;
}

const CHAT_MIN = 280;
const CHAT_MAX = 680;
const CHAT_DEFAULT = 380;

export function TopicContent({ onNavigate, topicId }: TopicContentProps) {
  // ── Layout ────────────────────────────────────────────────────────────
  const [showSyllabus, setShowSyllabus] = useState(true);
  const [showChat, setShowChat] = useState(false);
  const [chatWidth, setChatWidth] = useState(CHAT_DEFAULT);

  // ── Topic + PDF ───────────────────────────────────────────────────────
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [siblings, setSiblings] = useState<TopicSummary[]>([]);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  // ── Chat ─────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const chatCtrlRef = useRef<AbortController | null>(null);
  const streamingRef = useRef<string>(''); // mirrors streamingText for abort handler

  const id = topicId ? parseInt(topicId, 10) : null;

  // ── Resize drag ───────────────────────────────────────────────────────
  const isResizing = useRef(false);
  const resizeStartX = useRef(0);
  const resizeStartW = useRef(CHAT_DEFAULT);

  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    resizeStartX.current = e.clientX;
    resizeStartW.current = chatWidth;

    const onMove = (ev: MouseEvent) => {
      if (!isResizing.current) return;
      const maxW = Math.min(CHAT_MAX, Math.floor(window.innerWidth * 0.5));
      const delta = resizeStartX.current - ev.clientX;
      setChatWidth(Math.min(maxW, Math.max(CHAT_MIN, resizeStartW.current + delta)));
    };
    const onUp = () => {
      isResizing.current = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [chatWidth]);

  // ── Load topic, siblings, PDF, conversation ───────────────────────────
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setPdfUrl(null);
    setMessages([]);

    api.getTopic(id)
      .then(async (t) => {
        if (cancelled) return;
        setTopic(t);

        const sibs = await api.listTopics({ formLevel: t.formLevel, chapterId: t.chapterId });
        if (!cancelled) setSiblings(sibs);

        if (t.hasPdf) {
          try {
            const blobUrl = await api.getTopicPdfBlobUrl(t.topicId);
            if (!cancelled) setPdfUrl(blobUrl);
          } catch (e) {
            if (!cancelled)
              setError(e instanceof APIError ? e.message : 'PDF could not be loaded.');
          }
        }

        try {
          const conv = await api.getConversation(t.topicId);
          if (!cancelled) setMessages(conv.messages || []);
        } catch { /* empty conv is fine */ }
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof APIError ? err.message : 'Failed to load topic.');
      })
      .finally(() => { if (!cancelled) setIsLoading(false); });

    return () => {
      cancelled = true;
      chatCtrlRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Auto-scroll chat
  useEffect(() => {
    chatScrollRef.current?.scrollTo({ top: chatScrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, streamingText]);

  // Keep streamingRef in sync for the abort handler
  useEffect(() => {
    streamingRef.current = streamingText ?? '';
  }, [streamingText]);

  // ── Bookmark / complete ───────────────────────────────────────────────
  const handleToggleBookmark = async () => {
    if (!topic) return;
    const next = { ...topic, isBookmarked: !topic.isBookmarked };
    setTopic(next);
    try {
      if (next.isBookmarked) await api.bookmark(topic.topicId);
      else await api.unbookmark(topic.topicId);
    } catch { setTopic(topic); }
  };

  const handleToggleComplete = async () => {
    if (!topic) return;
    const next = { ...topic, isCompleted: !topic.isCompleted };
    setTopic(next);
    try {
      if (next.isCompleted) await api.markComplete(topic.topicId);
      else await api.unmarkComplete(topic.topicId);
    } catch { setTopic(topic); }
  };

  // ── Chat handlers ─────────────────────────────────────────────────────
  const handleSendMessage = () => {
    if (!topic || !chatInput.trim() || isSending) return;
    const question = chatInput.trim();
    setChatInput('');
    setIsSending(true);
    setStreamingText('');
    streamingRef.current = '';

    setMessages((prev) => [...prev, {
      messageId: -Date.now(),
      conversationId: 0,
      role: 'user',
      content: question,
      sourcePageStart: currentPage,
      sourcePageEnd: currentPage,
      validationStatus: 'na',
      validationWarning: null,
      createdAt: new Date().toISOString(),
    }]);

    chatCtrlRef.current = api.sendTutorMessage(
      topic.topicId,
      { question, currentPage },
      {
        onToken: (chunk) => setStreamingText((prev) => {
          const next = (prev ?? '') + chunk;
          streamingRef.current = next;
          return next;
        }),
        onReset: () => { setStreamingText(''); streamingRef.current = ''; },
        onFinal: (final) => {
          setMessages((prev) => [...prev, {
            messageId: -Date.now() - 1,
            conversationId: 0,
            role: 'assistant',
            content: final.content,
            sourcePageStart: final.sourcePageStart,
            sourcePageEnd: final.sourcePageEnd,
            validationStatus: final.validationStatus,
            validationWarning: final.validationWarning,
            createdAt: new Date().toISOString(),
          }]);
          setStreamingText(null);
          streamingRef.current = '';
          setIsSending(false);
        },
        onError: (msg) => {
          setMessages((prev) => [...prev, {
            messageId: -Date.now() - 2,
            conversationId: 0,
            role: 'assistant',
            content: `Maaf, terdapat ralat: ${msg}`,
            sourcePageStart: null,
            sourcePageEnd: null,
            validationStatus: 'warned',
            validationWarning: msg,
            createdAt: new Date().toISOString(),
          }]);
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
      setMessages((prev) => [...prev, {
        messageId: -Date.now() - 1,
        conversationId: 0,
        role: 'assistant',
        content: partial,
        sourcePageStart: null,
        sourcePageEnd: null,
        validationStatus: 'warned',
        validationWarning: 'Penjanaan dihentikan oleh pengguna.',
        createdAt: new Date().toISOString(),
      }]);
    }
    setStreamingText(null);
    streamingRef.current = '';
    setIsSending(false);
  };

  const handleClearChat = async () => {
    if (!topic || !confirm('Padam sejarah perbualan untuk topik ini?')) return;
    chatCtrlRef.current?.abort();
    try {
      await api.clearConversation(topic.topicId);
      setMessages([]);
      setStreamingText(null);
      streamingRef.current = '';
      setIsSending(false);
    } catch (e) { console.error(e); }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
  };

  const scale = useMemo(() => zoom / 100, [zoom]);

  if (!id) {
    return (
      <div className="p-8">
        <p>No topic selected.</p>
        <Button onClick={() => onNavigate('topics')}>Back to topics</Button>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#F9FAFB] overflow-hidden">

      {/* ── LEFT: Syllabus sidebar ─────────────────────────────────── */}
      {showSyllabus && (
        <aside className="w-72 flex-shrink-0 bg-white border-r border-[#E5E7EB] flex flex-col">
          <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
            <div>
              <div className="text-xs text-[#6B7280]">Form {topic?.formLevel ?? '—'}</div>
              <div className="font-bold text-[#111827]">Bab {topic?.chapterId ?? '—'}</div>
            </div>
            <button
              onClick={() => setShowSyllabus(false)}
              className="p-1 hover:bg-[#F3F4F6] rounded"
              title="Hide sidebar"
            >
              <ChevronLeft className="w-4 h-4 text-[#6B7280]" />
            </button>
          </div>
          <div className="px-4 py-3 text-xs uppercase tracking-wide text-[#6B7280]">Topics</div>
          <nav className="flex-1 overflow-y-auto px-2">
            {siblings.map((s) => {
              const isActive = topic?.topicId === s.topicId;
              return (
                <button
                  key={s.topicId}
                  onClick={() => onNavigate('topic-content', { topicId: String(s.topicId) })}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded text-left text-sm mb-1 ${
                    isActive
                      ? 'bg-[#EFF6FF] text-[#1E3A8A] font-medium'
                      : 'text-[#374151] hover:bg-[#F3F4F6]'
                  }`}
                >
                  <span className={`w-5 h-5 rounded border flex-shrink-0 flex items-center justify-center ${
                    s.isCompleted ? 'bg-[#059669] border-[#059669]' : 'border-[#D1D5DB]'
                  }`}>
                    {s.isCompleted && <Check className="w-3 h-3 text-white" />}
                  </span>
                  <span className="truncate">{s.topicName}</span>
                </button>
              );
            })}
          </nav>
        </aside>
      )}

      {/* ── MAIN COLUMN (header + PDF + chat row) ──────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-6 py-4 flex items-center gap-3 flex-shrink-0">
          <button
            onClick={() => onNavigate('topics')}
            className="p-2 hover:bg-[#F3F4F6] rounded flex-shrink-0"
            title="Back to topics"
          >
            <ArrowLeft className="w-5 h-5 text-[#6B7280]" />
          </button>

          {!showSyllabus && (
            <button
              onClick={() => setShowSyllabus(true)}
              className="text-sm text-[#1E3A8A] hover:underline flex-shrink-0"
            >
              Show topics
            </button>
          )}

          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-[#111827] truncate">{topic?.topicName ?? 'Loading…'}</h1>
            <p className="text-xs text-[#6B7280]">
              {topic ? `Bab ${topic.chapterId} · Form ${topic.formLevel}` : ''}
            </p>
          </div>

          <button
            onClick={handleToggleBookmark}
            className="p-2 hover:bg-[#F3F4F6] rounded flex-shrink-0"
          >
            {topic?.isBookmarked ? (
              <BookmarkCheck className="w-5 h-5 text-[#F59E0B]" fill="#F59E0B" />
            ) : (
              <Bookmark className="w-5 h-5 text-[#6B7280]" />
            )}
          </button>

          <Button
            onClick={handleToggleComplete}
            size="sm"
            className={`flex-shrink-0 ${
              topic?.isCompleted
                ? 'bg-[#059669] hover:bg-[#047857] text-white'
                : 'bg-[#1E3A8A] hover:bg-[#1E40AF] text-white'
            }`}
          >
            <Check className="w-4 h-4 mr-1" />
            {topic?.isCompleted ? 'Completed' : 'Mark as Complete'}
          </Button>

          {/* AI toggle — always accessible, no z-index clash */}
          <button
            onClick={() => setShowChat((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex-shrink-0 ${
              showChat
                ? 'bg-[#1E3A8A] text-white'
                : 'border border-[#E5E7EB] text-[#6B7280] hover:border-[#1E3A8A] hover:text-[#1E3A8A]'
            }`}
            title={showChat ? 'Close AI Tutor' : 'Open AI Tutor'}
          >
            <Bot className="w-4 h-4" />
            AI
          </button>
        </div>

        {/* PDF + Chat row */}
        <div className="flex-1 flex overflow-hidden">

          {/* PDF viewer */}
          <div className="flex-1 flex flex-col overflow-hidden min-w-0">
            <div className="flex-1 overflow-auto bg-[#F3F4F6] p-6 flex justify-center">
              {isLoading ? (
                <div className="text-[#6B7280] mt-12">Loading topic…</div>
              ) : error ? (
                <div className="p-6 rounded-lg bg-[#FEE2E2] border border-[#DC2626]/20 text-[#991B1B] max-w-xl h-fit">
                  {error}
                </div>
              ) : !topic?.hasPdf || !pdfUrl ? (
                <div className="bg-white rounded-xl shadow-edu-sm p-8 max-w-md h-fit text-center">
                  <FileWarning className="w-10 h-10 text-[#F59E0B] mx-auto mb-3" />
                  <p className="font-bold text-[#111827] mb-1">No PDF available yet</p>
                  <p className="text-sm text-[#6B7280]">
                    Drop a PDF into <code>backend/static/pdfs/</code> and run{' '}
                    <code>python -m scripts.ingest_pdf</code>.
                  </p>
                </div>
              ) : (
                <div className="bg-white shadow-edu-md">
                  <Document
                    file={pdfUrl}
                    onLoadSuccess={({ numPages: n }) => { setNumPages(n); setCurrentPage(1); }}
                    onLoadError={(err) => setError(`Failed to render PDF: ${err.message}`)}
                    loading={<div className="p-12 text-[#6B7280]">Rendering PDF…</div>}
                  >
                    <Page
                      pageNumber={currentPage}
                      scale={scale}
                      renderTextLayer
                      renderAnnotationLayer={false}
                    />
                  </Document>
                </div>
              )}
            </div>

            {topic?.hasPdf && pdfUrl && (
              <div className="bg-white border-t border-[#E5E7EB] px-6 py-3 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage <= 1}>
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-sm text-[#6B7280]">
                    Page {currentPage} of {numPages || '—'}
                  </span>
                  <Button size="sm" variant="ghost"
                    onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
                    disabled={!numPages || currentPage >= numPages}>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="ghost"
                    onClick={() => setZoom((z) => Math.max(50, z - 10))}>
                    <ZoomOut className="w-4 h-4" />
                  </Button>
                  <span className="text-sm text-[#6B7280] w-12 text-center">{zoom}%</span>
                  <Button size="sm" variant="ghost"
                    onClick={() => setZoom((z) => Math.min(200, z + 10))}>
                    <ZoomIn className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* ── Resize handle + Chat panel ─────────────────────────── */}
          {showChat && (
            <>
              {/* Draggable divider */}
              <div
                onMouseDown={handleResizeMouseDown}
                className="w-1.5 flex-shrink-0 bg-[#E5E7EB] hover:bg-[#1E3A8A] cursor-col-resize transition-colors"
                title="Drag to resize"
              />

              {/* Chat panel — maxWidth:50vw is the hard CSS cap; width is the user-dragged value */}
              <div
                style={{ width: chatWidth, maxWidth: '50vw', minWidth: CHAT_MIN }}
                className="flex-shrink-0 flex flex-col bg-white border-l border-[#E5E7EB] overflow-hidden"
              >
                {/* Chat header */}
                <div className="px-4 py-3 border-b border-[#E5E7EB] flex items-center gap-3 flex-shrink-0">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-[#111827] truncate">
                      {topic?.topicName ?? 'AI Tutor'}
                    </p>
                    <p className="text-xs text-[#059669]">Online · Bahasa Malaysia</p>
                  </div>
                  {messages.length > 0 && (
                    <button
                      onClick={handleClearChat}
                      className="p-1.5 hover:bg-[#FEE2E2] rounded-lg transition-colors flex-shrink-0"
                      title="Clear conversation"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-[#DC2626]" />
                    </button>
                  )}
                  <button
                    onClick={() => setShowChat(false)}
                    className="p-1.5 hover:bg-[#F3F4F6] rounded-lg transition-colors flex-shrink-0"
                    title="Close"
                  >
                    <X className="w-4 h-4 text-[#6B7280]" />
                  </button>
                </div>

                {/* Messages */}
                <div ref={chatScrollRef} className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-4 space-y-4">
                  {messages.length === 0 && streamingText === null && (
                    <div className="flex flex-col items-center justify-center py-10 text-center">
                      <Sparkles className="w-7 h-7 text-[#1E3A8A] mb-2" />
                      <p className="text-sm text-[#6B7280] leading-relaxed">
                        Tanya apa-apa tentang halaman yang anda baca sekarang. AI akan menjawab berdasarkan teks Bab ini.
                      </p>
                    </div>
                  )}

                  {messages.map((m) =>
                    m.role === 'user' ? (
                      <div key={m.messageId} className="flex justify-end">
                        <div className="max-w-[85%] bg-[#1E3A8A] text-white rounded-2xl rounded-tr-sm px-3.5 py-2.5 overflow-hidden">
                          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words w-full">{m.content}</p>
                        </div>
                      </div>
                    ) : (
                      <div key={m.messageId} className="flex gap-2 min-w-0">
                        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Bot className="w-3.5 h-3.5 text-white" />
                        </div>
                        <div className="flex-1 min-w-0 overflow-hidden">
                          <div className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-2xl rounded-tl-sm px-3.5 py-2.5 overflow-hidden">
                            <MarkdownMessage content={m.content} />
                          </div>
                          {/* Source page badge */}
                          {m.sourcePageStart != null && (
                            <p className="text-[10px] text-[#9CA3AF] mt-1 px-1">
                              Rujukan: Hlm {m.sourcePageStart}
                              {m.sourcePageEnd != null && m.sourcePageEnd !== m.sourcePageStart
                                ? `–${m.sourcePageEnd}`
                                : ''}
                            </p>
                          )}
                          {m.validationStatus === 'warned' && (
                            <div className="mt-1 flex items-start gap-1 px-1">
                              <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
                              <p className="text-xs text-amber-700 break-words">
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
                    <div className="flex gap-2 min-w-0">
                      <div className={`w-6 h-6 rounded-full bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center flex-shrink-0 mt-0.5 ${streamingText === '' ? 'animate-pulse' : ''}`}>
                        <Bot className="w-3.5 h-3.5 text-white" />
                      </div>
                      <div className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-2xl rounded-tl-sm px-3.5 py-2.5 flex-1 min-w-0 overflow-hidden min-h-[36px]">
                        {streamingText === '' ? (
                          /* Typing dots */
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

                {/* Input */}
                <div className="px-3 py-3 border-t border-[#E5E7EB] flex-shrink-0 bg-white">
                  <div className="flex gap-2 items-end bg-[#F9FAFB] border border-[#E5E7EB] rounded-xl px-3 py-2.5 focus-within:border-[#1E3A8A] focus-within:bg-white transition-colors">
                    <textarea
                      value={chatInput}
                      onChange={(e) => {
                        setChatInput(e.target.value);
                        e.target.style.height = 'auto';
                        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                      }}
                      onKeyDown={handleKeyDown}
                      placeholder="Tanya apa-apa tentang bab ini…"
                      disabled={isSending}    // kept: Enter-to-send blocked during generation
                      rows={1}
                      className="flex-1 min-w-0 bg-transparent text-sm text-[#111827] placeholder-[#9CA3AF] resize-none focus:outline-none disabled:opacity-50"
                      style={{ maxHeight: '120px' }}
                    />
                    {isSending ? (
                      <button
                        onClick={handleAbort}
                        className="w-7 h-7 bg-[#DC2626] rounded-lg flex items-center justify-center flex-shrink-0 hover:bg-[#B91C1C] transition-colors"
                        title="Hentikan penjanaan"
                      >
                        <Square className="w-3 h-3 text-white fill-white" />
                      </button>
                    ) : (
                      <button
                        onClick={handleSendMessage}
                        disabled={!chatInput.trim()}
                        className="w-7 h-7 bg-[#1E3A8A] rounded-lg flex items-center justify-center flex-shrink-0 hover:bg-[#1E40AF] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        <Send className="w-3.5 h-3.5 text-white" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
