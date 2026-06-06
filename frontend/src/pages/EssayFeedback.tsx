import { useState, useEffect, useRef } from 'react';
import { AppSidebar } from '../components/AppSidebar';
import { CircularProgress } from '../components/CircularProgress';
import { Button } from '../components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Check, X, AlertTriangle, Loader2, Minus } from 'lucide-react';
import { api, EssayAttempt, MatchedNode, ArasDescriptorScores } from '../lib/api';

interface EssayFeedbackProps {
  onNavigate: (page: any, params?: any) => void;
  attemptId: string | null;
}

export function EssayFeedback({ onNavigate, attemptId }: EssayFeedbackProps) {
  const [attempt, setAttempt] = useState<EssayAttempt | null>(null);
  const [loading, setLoading] = useState(true);
  const [gradingMsg, setGradingMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<AbortController | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearPolling = () => {
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    if (fallbackTimerRef.current) { clearTimeout(fallbackTimerRef.current); fallbackTimerRef.current = null; }
  };

  useEffect(() => {
    if (!attemptId) { setError('No attempt selected.'); setLoading(false); return; }
    const aId = parseInt(attemptId, 10);
    let cancelled = false;

    api.getEssayAttempt(aId)
      .then((a) => {
        if (cancelled) return;
        setAttempt(a);
        if (a.gradingStatus !== 'done' && a.gradingStatus !== 'failed') {
          startStream(aId);
        }
      })
      .catch((err) => { if (!cancelled) setError(err.message ?? 'Failed to load attempt.'); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; streamRef.current?.abort(); clearPolling(); };
  }, [attemptId]); // eslint-disable-line react-hooks/exhaustive-deps

  const startStream = (aId: number) => {
    setGradingMsg('Sedang menilai jawapan anda…');
    streamRef.current = api.streamEssayGrading(aId, {
      onStatus: (info) => setGradingMsg(`Status: ${info.gradingStatus}`),
      onDone: (finalAttempt) => {
        clearPolling();
        setAttempt(finalAttempt);
        setGradingMsg(null);
      },
      onError: (msg) => {
        clearPolling();
        setError(msg);
        setGradingMsg(null);
      },
    });

    // Polling fallback: if SSE doesn't resolve within 30 s, poll REST every 5 s
    fallbackTimerRef.current = setTimeout(() => {
      pollingRef.current = setInterval(async () => {
        try {
          const a = await api.getEssayAttempt(aId);
          if (a.gradingStatus === 'done') {
            clearPolling();
            setAttempt(a);
            setGradingMsg(null);
          } else if (a.gradingStatus === 'failed') {
            clearPolling();
            setGradingMsg(null);
            setAttempt((prev) => prev ? { ...prev, gradingStatus: 'failed' } : prev);
          }
        } catch { /* ignore transient polling errors */ }
      }, 5_000);
    }, 30_000);
  };

  const handleRetryGrading = async () => {
    if (!attempt) return;
    const aId = attempt.attemptId;
    try {
      await api.retryEssayGrading(aId);
      setError(null);
      setAttempt((prev) => prev ? { ...prev, gradingStatus: 'pending' } : prev);
      clearPolling();
      startStream(aId);
    } catch (err: any) {
      setError(err.message ?? 'Failed to retry grading.');
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F9FAFB]">
        <Loader2 className="w-8 h-8 animate-spin text-[#1E3A8A]" />
      </div>
    );
  }

  if (error || !attempt) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F9FAFB]">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error ?? 'Attempt not found.'}</p>
          <Button onClick={() => onNavigate('essay-practice')} variant="outline">
            Kembali ke Essay Practice
          </Button>
        </div>
      </div>
    );
  }

  const question = attempt.question;
  const isStruktur = question?.questionType === 'struktur';
  const isGraded = attempt.gradingStatus === 'done';
  const scorePct =
    isGraded && attempt.score != null && attempt.maxScore
      ? Math.round((attempt.score / attempt.maxScore) * 100)
      : 0;

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="essay-practice" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827]">Maklum Balas Esei</h1>
          <p className="text-[#6B7280] mt-1 text-sm line-clamp-2">
            {question?.questionText ?? ''}
          </p>
        </div>

        <div className="p-8 max-w-5xl mx-auto space-y-8">
          {/* Grading in progress */}
          {gradingMsg && (
            <div className="bg-blue-50 border border-blue-200 text-blue-800 rounded-xl p-6 flex items-center gap-4">
              <Loader2 className="w-6 h-6 animate-spin flex-shrink-0" />
              <div>
                <p className="font-semibold">Penilaian sedang dijalankan…</p>
                <p className="text-sm mt-1">{gradingMsg}</p>
              </div>
            </div>
          )}

          {/* Grading failed */}
          {attempt.gradingStatus === 'failed' && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-6 flex items-center justify-between gap-4">
              <span>Penilaian gagal. Sila cuba semula.</span>
              <Button
                onClick={handleRetryGrading}
                size="sm"
                className="bg-red-700 hover:bg-red-800 text-white flex-shrink-0"
              >
                Cuba Semula
              </Button>
            </div>
          )}

          {/* Score header */}
          {isGraded && attempt.score != null && (
            <div className="bg-white rounded-xl shadow-edu-md p-8">
              <div className="flex items-center gap-8">
                <CircularProgress percentage={scorePct} size="large" />
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="text-3xl font-bold text-[#111827]">
                      {Math.round(attempt.score ?? 0)}/{attempt.maxScore}
                    </h2>
                    {!isStruktur && attempt.arasLevel && (
                      <span className="px-3 py-1 bg-[#1E3A8A] text-white rounded-full text-sm font-bold">
                        Aras {attempt.arasLevel}
                      </span>
                    )}
                  </div>

                  {/* Note-form penalty banner */}
                  {attempt.isNoteForm && (
                    <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mt-3 text-sm">
                      <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                      <span>
                        <strong>Jawapan dalam bentuk nota/poin</strong> — had markah Aras 2 (maksimum 4 markah)
                        mengikut skema pemarkahan SPM Sejarah Kertas 2.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tabs */}
          {isGraded && (
            <Tabs defaultValue="feedback">
              <TabsList className="bg-white border border-[#E5E7EB] mb-6">
                <TabsTrigger value="response">Jawapan Anda</TabsTrigger>
                <TabsTrigger value="feedback">Maklum Balas</TabsTrigger>
                {isStruktur && attempt.matchedNodes && attempt.matchedNodes.length > 0 && (
                  <TabsTrigger value="codes">Pemarkahan F/H/C</TabsTrigger>
                )}
                <TabsTrigger value="model">Jawapan Model</TabsTrigger>
              </TabsList>

              {/* Tab: Jawapan Anda */}
              <TabsContent value="response">
                <div className="bg-white rounded-xl shadow-edu-sm p-6">
                  <p className="text-[#111827] leading-relaxed whitespace-pre-wrap text-sm">
                    {attempt.responseText || <span className="text-[#9CA3AF]">(Tiada teks)</span>}
                  </p>
                </div>
              </TabsContent>

              {/* Tab: Maklum Balas */}
              <TabsContent value="feedback">
                <FeedbackPanel attempt={attempt} isStruktur={isStruktur} />
              </TabsContent>

              {/* Tab: Pemarkahan F/H/C (struktur only) */}
              {isStruktur && attempt.matchedNodes && attempt.matchedNodes.length > 0 && (
                <TabsContent value="codes">
                  <CodeTreePanel
                    nodes={attempt.matchedNodes}
                    score={attempt.score ?? 0}
                    maxScore={attempt.maxScore ?? 0}
                  />
                </TabsContent>
              )}

              {/* Tab: Jawapan Model */}
              <TabsContent value="model">
                <div className="bg-white rounded-xl shadow-edu-sm p-6">
                  <div className="bg-[#EFF6FF] border-l-4 border-[#1E3A8A] p-3 rounded mb-4 text-sm text-[#1E3A8A] font-medium">
                    Jawapan model yang memenuhi kriteria markah penuh
                  </div>
                  <p className="text-[#111827] leading-relaxed whitespace-pre-wrap text-sm">
                    {question?.modelAnswer ?? '—'}
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          )}

          {/* Action buttons */}
          <div className="flex gap-4">
            {question && (
              <Button
                onClick={() => onNavigate('essay-writing', { questionId: String(question.questionId) })}
                variant="outline"
                className="flex-1"
              >
                Cuba Lagi
              </Button>
            )}
            <Button
              onClick={() => onNavigate('essay-practice')}
              className="flex-1 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              Kembali ke Essay Practice
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Feedback panel ────────────────────────────────────────────────────────────

function FeedbackPanel({
  attempt,
  isStruktur,
}: {
  attempt: EssayAttempt;
  isStruktur: boolean;
}) {
  const fb = attempt.feedbackJson;
  if (!fb) return <p className="text-[#9CA3AF]">Tiada maklum balas.</p>;

  return (
    <div className="space-y-6">
      {/* Strengths */}
      {fb.strengths && fb.strengths.length > 0 && (
        <div className="bg-white rounded-xl shadow-edu-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[#D1FAE5] rounded-full flex items-center justify-center">
              <Check className="w-5 h-5 text-[#059669]" />
            </div>
            <h3 className="text-lg font-bold text-[#111827]">Kekuatan</h3>
          </div>
          <ul className="space-y-2">
            {fb.strengths.map((s, i) => (
              <li key={i} className="flex gap-3 text-[#374151] text-sm">
                <span className="text-[#059669] font-bold flex-shrink-0">✓</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Improvements */}
      {fb.improvements && fb.improvements.length > 0 && (
        <div className="bg-white rounded-xl shadow-edu-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[#FEF3C7] rounded-full flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-[#F59E0B]" />
            </div>
            <h3 className="text-lg font-bold text-[#111827]">Cadangan Penambahbaikan</h3>
          </div>
          <ul className="space-y-2">
            {fb.improvements.map((s, i) => (
              <li key={i} className="flex gap-3 text-[#374151] text-sm">
                <span className="text-[#F59E0B] font-bold flex-shrink-0">△</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Detailed feedback */}
      {fb.detailedFeedback && (
        <div className="bg-white rounded-xl shadow-edu-sm p-6">
          <h3 className="text-lg font-bold text-[#111827] mb-3">Maklum Balas Terperinci</h3>
          <p className="text-[#374151] leading-relaxed text-sm">{fb.detailedFeedback}</p>
        </div>
      )}

      {/* Esei: Aras descriptor table */}
      {!isStruktur && fb.arasDescriptorScores && (
        <ArasDescriptorTable
          scores={fb.arasDescriptorScores}
          arasLevel={attempt.arasLevel}
          scoreValue={attempt.score}
          reasoning={fb.arasReasoning}
        />
      )}
    </div>
  );
}

// ── Aras descriptor breakdown table (esei only) ───────────────────────────────

const DESCRIPTOR_LABELS: Record<keyof ArasDescriptorScores, string> = {
  pengetahuan_pemahaman: 'Pengetahuan & Pemahaman',
  bukti_contoh: 'Bukti / Contoh',
  membuat_inferens: 'Membuat Inferens',
  kedalaman_jawapan: 'Kedalaman Jawapan',
  komunikasi_pengolahan: 'Komunikasi / Pengolahan',
  kematangan: 'Kematangan',
};

function ArasDescriptorTable({
  scores,
  arasLevel,
  scoreValue,
  reasoning,
}: {
  scores: ArasDescriptorScores;
  arasLevel?: number | null;
  scoreValue?: number | null;
  reasoning?: string;
}) {
  const rows = Object.entries(DESCRIPTOR_LABELS) as [keyof ArasDescriptorScores, string][];

  function renderValue(key: keyof ArasDescriptorScores, val: string | boolean) {
    if (key === 'kematangan') {
      return val ? (
        <span className="text-[#059669] flex items-center gap-1"><Check className="w-4 h-4" /> ada</span>
      ) : (
        <span className="text-[#9CA3AF] flex items-center gap-1"><X className="w-4 h-4" /> tidak</span>
      );
    }
    const v = String(val);
    const positive = ['sangat jelas', 'sangat sesuai', 'sangat menarik', 'sangat mendalam', 'tepat', 'mendalam', 'menarik', 'jelas', 'sesuai', 'ada'].some((w) =>
      v.toLowerCase().includes(w)
    );
    const icon = positive ? (
      <Check className="w-4 h-4 text-[#059669] flex-shrink-0" />
    ) : (
      <Minus className="w-4 h-4 text-[#9CA3AF] flex-shrink-0" />
    );
    return (
      <span className="flex items-center gap-1.5 text-[#374151]">
        {icon} {v}
      </span>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-edu-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-[#E5E7EB]">
        <h3 className="text-lg font-bold text-[#111827]">Kriteria Penilaian SPM</h3>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-[#F9FAFB]">
          <tr>
            <th className="text-left px-6 py-3 text-[#6B7280] font-medium">Kriteria</th>
            <th className="text-left px-6 py-3 text-[#6B7280] font-medium">Penilaian Anda</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E5E7EB]">
          {rows.map(([key, label]) => (
            <tr key={key}>
              <td className="px-6 py-3 text-[#374151]">{label}</td>
              <td className="px-6 py-3">{renderValue(key, (scores as any)[key])}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-[#EFF6FF]">
          <tr>
            <td colSpan={2} className="px-6 py-3 font-semibold text-[#1E3A8A]">
              {arasLevel != null && `Aras ${arasLevel}`}
              {scoreValue != null && ` · ${Math.round(scoreValue)} markah`}
            </td>
          </tr>
        </tfoot>
      </table>
      {reasoning && (
        <div className="px-6 py-4 border-t border-[#E5E7EB] text-sm text-[#374151] bg-[#FAFAFA]">
          <span className="font-medium text-[#111827]">Alasan Pemeriksa: </span>
          {reasoning}
        </div>
      )}
    </div>
  );
}

// ── F/H/C recursive code tree (struktur only) ─────────────────────────────────

function CodeTreePanel({
  nodes,
  score,
  maxScore,
}: {
  nodes: MatchedNode[];
  score: number;
  maxScore: number;
}) {
  return (
    <div className="bg-white rounded-xl shadow-edu-sm p-6">
      <h3 className="text-lg font-bold text-[#111827] mb-4">Semakan Kod F/H/C</h3>
      <div className="space-y-1 mb-4">
        {nodes.map((n) => (
          <MatchedNodeRow key={n.code} node={n} depth={0} />
        ))}
      </div>
      <div className="border-t border-[#E5E7EB] pt-4 text-right">
        <span className="text-lg font-bold text-[#111827]">
          {score} / {maxScore} markah
        </span>
      </div>
    </div>
  );
}

function MatchedNodeRow({ node, depth }: { node: MatchedNode; depth: number }) {
  const icon = node.matched ? (
    <Check className="w-4 h-4 text-[#059669] flex-shrink-0" />
  ) : (
    <X className="w-4 h-4 text-[#EF4444] flex-shrink-0" />
  );

  const typeColors: Record<string, string> = {
    F: 'font-semibold text-[#111827]',
    H: 'text-[#374151]',
    C: 'text-[#6B7280] italic text-sm',
  };

  return (
    <div>
      <div
        style={{ paddingLeft: `${depth * 20}px` }}
        className={`flex items-start gap-2 py-1 ${typeColors[node.type] ?? ''}`}
      >
        {icon}
        <span className="font-mono text-xs bg-[#F3F4F6] px-1.5 py-0.5 rounded flex-shrink-0 self-start mt-0.5">
          {node.code}
        </span>
        <div className="flex-1 min-w-0">
          <span>{node.text}</span>
          {node.matched && node.evidence && (
            <p className="text-xs text-[#6B7280] mt-0.5 italic">
              "…{node.evidence}…"
            </p>
          )}
        </div>
      </div>
      {(node.children ?? []).map((child) => (
        <MatchedNodeRow key={child.code} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}
