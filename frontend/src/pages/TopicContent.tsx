import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft, Bookmark, BookmarkCheck, Check, ChevronLeft, ChevronRight,
  X, ZoomIn, ZoomOut, Bot, FileWarning,
} from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { Button } from '../components/ui/button';
import { api, TopicDetail, TopicSummary, APIError } from '../lib/api';

// react-pdf needs the worker. We point it at the CDN copy that matches
// pdfjs-dist's version. (If your network blocks CDNs, see README for the
// local-worker variant.)
pdfjs.GlobalWorkerOptions.workerSrc =
  `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

interface TopicContentProps {
  onNavigate: (page: any) => void;
  topicId: string | null;
}

export function TopicContent({ onNavigate, topicId }: TopicContentProps) {
  // --- Layout toggles ---
  const [showSyllabus, setShowSyllabus] = useState(true);
  const [showChat, setShowChat] = useState(true);

  // --- Data ---
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [siblings, setSiblings] = useState<TopicSummary[]>([]);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // --- Viewer state ---
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  const id = topicId ? parseInt(topicId, 10) : null;

  // Fetch topic detail + sibling topics in the same chapter
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setPdfUrl(null);

    api
      .getTopic(id)
      .then(async (t) => {
        if (cancelled) return;
        setTopic(t);
        // Siblings
        const sibs = await api.listTopics({
          formLevel: t.formLevel,
          chapterId: t.chapterId,
        });
        if (!cancelled) setSiblings(sibs);

        // PDF blob (auth-protected, can't use the URL directly)
        if (t.hasPdf) {
          try {
            const blobUrl = await api.getTopicPdfBlobUrl(t.topicId);
            if (!cancelled) setPdfUrl(blobUrl);
          } catch (e) {
            if (!cancelled)
              setError(e instanceof APIError ? e.message : 'PDF could not be loaded.');
          }
        }
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof APIError ? err.message : 'Failed to load topic.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
      // Free the blob URL so we don't leak memory
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleToggleBookmark = async () => {
    if (!topic) return;
    const next = { ...topic, isBookmarked: !topic.isBookmarked };
    setTopic(next);
    try {
      if (next.isBookmarked) await api.bookmark(topic.topicId);
      else await api.unbookmark(topic.topicId);
    } catch {
      setTopic(topic); // revert
    }
  };

  const handleToggleComplete = async () => {
    if (!topic) return;
    const next = { ...topic, isCompleted: !topic.isCompleted };
    setTopic(next);
    try {
      if (next.isCompleted) await api.markComplete(topic.topicId);
      else await api.unmarkComplete(topic.topicId);
    } catch {
      setTopic(topic);
    }
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
    <div className="flex h-screen bg-[#F9FAFB]">
      {/* ===================== LEFT: Sibling topics ===================== */}
      {showSyllabus && (
        <aside className="w-72 bg-white border-r border-[#E5E7EB] flex flex-col">
          <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
            <div>
              <div className="text-xs text-[#6B7280]">
                Form {topic?.formLevel ?? '—'}
              </div>
              <div className="font-bold text-[#111827]">
                Bab {topic?.chapterId ?? '—'}
              </div>
            </div>
            <button
              onClick={() => setShowSyllabus(false)}
              className="p-1 hover:bg-[#F3F4F6] rounded"
              title="Hide sidebar"
            >
              <ChevronLeft className="w-4 h-4 text-[#6B7280]" />
            </button>
          </div>
          <div className="px-4 py-3 text-xs uppercase tracking-wide text-[#6B7280]">
            Topics
          </div>
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
                  <span
                    className={`w-5 h-5 rounded border flex-shrink-0 flex items-center justify-center ${
                      s.isCompleted
                        ? 'bg-[#059669] border-[#059669]'
                        : 'border-[#D1D5DB]'
                    }`}
                  >
                    {s.isCompleted && <Check className="w-3 h-3 text-white" />}
                  </span>
                  <span className="truncate">{s.topicName}</span>
                </button>
              );
            })}
          </nav>
        </aside>
      )}

      {/* ===================== CENTRE: PDF viewer ===================== */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="bg-white border-b border-[#E5E7EB] px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => onNavigate('topics')}
            className="p-2 hover:bg-[#F3F4F6] rounded"
            title="Back to topics"
          >
            <ArrowLeft className="w-5 h-5 text-[#6B7280]" />
          </button>
          {!showSyllabus && (
            <button
              onClick={() => setShowSyllabus(true)}
              className="text-sm text-[#1E3A8A] hover:underline"
            >
              Show topics
            </button>
          )}
          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-[#111827] truncate">
              {topic?.topicName ?? 'Loading…'}
            </h1>
            <p className="text-xs text-[#6B7280]">
              {topic ? `Bab ${topic.chapterId} • Form ${topic.formLevel}` : ''}
            </p>
          </div>
          <button
            onClick={handleToggleBookmark}
            className="p-2 hover:bg-[#F3F4F6] rounded"
            title={topic?.isBookmarked ? 'Remove bookmark' : 'Bookmark this topic'}
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
            className={
              topic?.isCompleted
                ? 'bg-[#059669] hover:bg-[#047857] text-white'
                : 'bg-[#1E3A8A] hover:bg-[#1E40AF] text-white'
            }
          >
            <Check className="w-4 h-4 mr-1" />
            {topic?.isCompleted ? 'Completed' : 'Mark as Complete'}
          </Button>
          {!showChat && (
            <button
              onClick={() => setShowChat(true)}
              className="p-2 hover:bg-[#F3F4F6] rounded"
              title="Show AI Tutor"
            >
              <Bot className="w-5 h-5 text-[#6B7280]" />
            </button>
          )}
        </div>

        {/* Viewer body */}
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
                Drop a PDF into <code>backend/static/pdfs/{topic?.formLevel ? `Form${topic.formLevel}/Bab${topic.chapterId}/` : ''}</code>
                {' '}and run <code>python -m scripts.ingest_pdf</code>.
              </p>
            </div>
          ) : (
            <div className="bg-white shadow-edu-md">
              <Document
                file={pdfUrl}
                onLoadSuccess={({ numPages }) => {
                  setNumPages(numPages);
                  setCurrentPage(1);
                }}
                onLoadError={(err) =>
                  setError(`Failed to render PDF: ${err.message}`)
                }
                loading={<div className="p-12 text-[#6B7280]">Rendering PDF…</div>}
              >
                <Page
                  pageNumber={currentPage}
                  scale={scale}
                  renderTextLayer={true}
                  renderAnnotationLayer={false}
                />
              </Document>
            </div>
          )}
        </div>

        {/* Bottom toolbar */}
        {topic?.hasPdf && pdfUrl && (
          <div className="bg-white border-t border-[#E5E7EB] px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-[#6B7280]">
                Page {currentPage} of {numPages || '—'}
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
                disabled={!numPages || currentPage >= numPages}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setZoom((z) => Math.max(50, z - 10))}
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
              <span className="text-sm text-[#6B7280] w-12 text-center">{zoom}%</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setZoom((z) => Math.min(200, z + 10))}
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </main>

      {/* ===================== RIGHT: AI Tutor placeholder ===================== */}
      {showChat && (
        <aside className="w-80 bg-white border-l border-[#E5E7EB] flex flex-col">
          <div className="p-4 border-b border-[#E5E7EB] flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <p className="font-bold text-[#111827]">AI Tutor</p>
              <p className="text-xs text-[#9CA3AF]">Offline — Phase 3</p>
            </div>
            <button
              onClick={() => setShowChat(false)}
              className="p-1 hover:bg-[#F3F4F6] rounded"
            >
              <X className="w-4 h-4 text-[#6B7280]" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 text-sm text-[#6B7280]">
            <p className="bg-[#F3F4F6] rounded-lg p-3">
              The AI Tutor will be wired up in Phase 3 (Week 7+) once Ollama and
              LangChain are in place. It will read the current page
              ({`page ${currentPage}`}) and answer questions about it.
            </p>
          </div>
          <div className="p-4 border-t border-[#E5E7EB]">
            <input
              disabled
              placeholder="Available in Phase 3…"
              className="w-full px-3 py-2 rounded-lg border border-[#E5E7EB] bg-[#F9FAFB] text-sm text-[#9CA3AF]"
            />
          </div>
        </aside>
      )}
    </div>
  );
}