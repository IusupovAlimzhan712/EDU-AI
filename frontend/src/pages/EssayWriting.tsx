import { useState, useEffect, useRef, useCallback } from 'react';
import { ArrowLeft, Save, Send, Clock, Loader2, AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { api, EssayQuestion, EssayAttempt, CodeNode } from '../lib/api';

interface EssayWritingProps {
  onNavigate: (page: any, params?: any) => void;
  questionId: string | null;
}

const NOTE_LINE_RE = /^\s*([-•*]|\d+\.|[a-zA-Z]\)|\(\w\))\s/;

function isNoteFormText(text: string): boolean {
  const lines = text.split('\n').filter((l) => l.trim().length > 0);
  if (lines.length === 0) return false;
  const noteLines = lines.filter((l) => NOTE_LINE_RE.test(l));
  return noteLines.length / lines.length >= 0.3;
}

export function EssayWriting({ onNavigate, questionId }: EssayWritingProps) {
  const [question, setQuestion] = useState<EssayQuestion | null>(null);
  const [attempt, setAttempt] = useState<EssayAttempt | null>(null);
  const [responseText, setResponseText] = useState('');
  const [timeSpent, setTimeSpent] = useState(0);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptIdRef = useRef<number | null>(null);

  // Load question + start/resume attempt
  useEffect(() => {
    if (!questionId) { setError('No question selected.'); setLoading(false); return; }
    const qId = parseInt(questionId, 10);

    Promise.all([api.getEssayQuestion(qId), api.startEssayAttempt(qId)])
      .then(([q, a]) => {
        setQuestion(q);
        setAttempt(a);
        attemptIdRef.current = a.attemptId;
        setResponseText(a.responseText ?? '');
      })
      .catch((err) => setError(err.message ?? 'Failed to load question.'))
      .finally(() => setLoading(false));
  }, [questionId]);

  // Timer
  useEffect(() => {
    const t = setInterval(() => setTimeSpent((p) => p + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Auto-save every 30 s
  const saveDraft = useCallback(async (text: string) => {
    if (!attemptIdRef.current) return;
    setSaving(true);
    try {
      await api.saveEssayDraft(attemptIdRef.current, text);
      setLastSaved(new Date());
    } catch { /* silently ignore */ }
    setSaving(false);
  }, []);

  useEffect(() => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(() => saveDraft(responseText), 30_000);
    return () => { if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current); };
  }, [responseText, saveDraft]);

  const handleSave = async () => {
    await saveDraft(responseText);
  };

  const handleSubmit = async () => {
    if (!attempt) return;
    if (!window.confirm('Hantar jawapan untuk penilaian? Anda tidak boleh mengubah jawapan selepas ini.')) return;
    setSubmitting(true);
    try {
      await api.saveEssayDraft(attempt.attemptId, responseText);
      await api.submitEssayAttempt(attempt.attemptId);
      onNavigate('essay-feedback', { attemptId: String(attempt.attemptId) });
    } catch (err: any) {
      setError(err.message ?? 'Failed to submit.');
      setSubmitting(false);
    }
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  const wordCount = responseText.trim() ? responseText.trim().split(/\s+/).length : 0;
  const noteFormWarning = question?.questionType === 'esei' && wordCount > 10 && isNoteFormText(responseText);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#F9FAFB]">
        <Loader2 className="w-8 h-8 animate-spin text-[#1E3A8A]" />
      </div>
    );
  }

  if (error || !question) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#F9FAFB]">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error ?? 'Question not found.'}</p>
          <Button onClick={() => onNavigate('essay-practice')} variant="outline">
            Back to Essay Practice
          </Button>
        </div>
      </div>
    );
  }

  const isStruktur = question.questionType === 'struktur';

  return (
    <div className="h-screen bg-[#F9FAFB] flex">
      {/* Left Panel - Question + Marking Info */}
      <div className="w-[40%] bg-white border-r border-[#E5E7EB] flex flex-col">
        <div className="p-6 border-b border-[#E5E7EB]">
          <button
            onClick={() => onNavigate('essay-practice')}
            className="flex items-center gap-2 text-[#6B7280] hover:text-[#374151] mb-4 transition-default"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Kembali ke Essay Practice</span>
          </button>

          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                isStruktur ? 'bg-[#DBEAFE] text-[#1E3A8A]' : 'bg-[#EDE9FE] text-[#7C3AED]'
              }`}
            >
              {isStruktur ? 'Soalan Struktur' : 'Soalan Esei'}
            </span>
            <span className="px-3 py-1 bg-[#F3F4F6] text-[#6B7280] rounded-full text-xs font-medium">
              [{question.maxMarks} markah]
            </span>
            <span className="px-3 py-1 bg-[#F3F4F6] text-[#6B7280] rounded-full text-xs font-medium">
              {question.subQuestion}
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div>
            <h2 className="text-lg font-bold text-[#111827] leading-snug">
              {question.questionText}
            </h2>
          </div>

          {/* Marking criteria panel */}
          {isStruktur ? (
            <StrukturCriteriaPanel question={question} />
          ) : (
            <EseiCriteriaPanel maxMarks={question.maxMarks} />
          )}
        </div>
      </div>

      {/* Right Panel - Writing Area */}
      <div className="flex-1 flex flex-col">
        <div className="bg-white border-b border-[#E5E7EB] p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-bold text-[#111827]">Jawapan Anda</h3>
            <div className="flex items-center gap-4 text-sm text-[#6B7280]">
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                <span>{formatTime(timeSpent)}</span>
              </div>
              {saving && <span className="text-[#9CA3AF]">Menyimpan…</span>}
              {lastSaved && !saving && (
                <span className="text-[#059669]">
                  Disimpan {lastSaved.toLocaleTimeString('ms-MY', { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>
          </div>
          <div className="text-sm text-[#6B7280]">
            Bilangan perkataan:{' '}
            <span className={`font-bold ${wordCount >= 150 ? 'text-[#059669]' : 'text-[#6B7280]'}`}>
              {wordCount}
            </span>
          </div>
        </div>

        {/* Note-form warning (esei only) */}
        {noteFormWarning && (
          <div className="mx-6 mt-4 flex items-start gap-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-4">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <span className="font-semibold">Amaran: Bentuk Nota/Poin Dikesan</span>
              <p className="mt-1">
                Soalan esei mesti dijawab dalam bentuk karangan (prosa berterusan). Jawapan dalam bentuk
                poin atau senarai akan dihadkan kepada Aras 2 (maksimum 4 markah) mengikut skema pemarkahan SPM.
              </p>
            </div>
          </div>
        )}

        <div className="flex-1 p-6">
          <Textarea
            value={responseText}
            onChange={(e) => setResponseText(e.target.value)}
            placeholder={
              isStruktur
                ? 'Tulis jawapan anda di sini dalam Bahasa Malaysia…'
                : 'Tulis karangan anda di sini dalam bentuk prosa berterusan (bukan poin)…'
            }
            className="w-full h-full resize-none text-base leading-relaxed"
            disabled={submitting}
          />
        </div>

        <div className="bg-white border-t border-[#E5E7EB] p-6">
          <div className="flex justify-between items-center">
            <Button onClick={handleSave} variant="outline" disabled={saving || submitting}>
              <Save className="w-4 h-4 mr-2" />
              Simpan Draf
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={wordCount < 20 || submitting}
              className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
            >
              {submitting ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Menghantar…</>
              ) : (
                <><Send className="w-4 h-4 mr-2" />Hantar untuk Penilaian</>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Struktur marking criteria panel ──────────────────────────────────────────

function StrukturCriteriaPanel({ question }: { question: EssayQuestion }) {
  const { nodes, maxMarks } = question.markingScheme;
  const topLevelCount = nodes.length;

  return (
    <div>
      <h3 className="font-semibold text-[#111827] mb-3">Kriteria Pemarkahan</h3>
      <div className="bg-[#EFF6FF] border-l-4 border-[#1E3A8A] p-3 rounded mb-4 text-sm text-[#1E3A8A]">
        Mana-mana <strong>{maxMarks} × 1 markah</strong> — jawab mana-mana{' '}
        {maxMarks} fakta/huraian yang betul.
      </div>
      {nodes.length > 0 ? (
        <div className="space-y-2">
          {nodes.map((node) => (
            <CodeNodeItem key={node.code} node={node} depth={0} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-[#9CA3AF]">Skema pemarkahan sedang dimuat…</p>
      )}
      <p className="text-xs text-[#9CA3AF] mt-3">
        {topLevelCount} kategori utama • {maxMarks} markah maksimum
      </p>
    </div>
  );
}

function CodeNodeItem({ node, depth }: { node: CodeNode; depth: number }) {
  const colors: Record<string, string> = {
    F: 'text-[#1E3A8A] font-semibold',
    H: 'text-[#374151]',
    C: 'text-[#6B7280] italic',
  };
  return (
    <div style={{ paddingLeft: `${depth * 16}px` }}>
      <div className={`text-sm flex gap-2 ${colors[node.type] ?? ''}`}>
        <span className="flex-shrink-0 font-mono text-xs bg-[#F3F4F6] px-1.5 py-0.5 rounded self-start mt-0.5">
          {node.code}
        </span>
        <span>{node.text}</span>
      </div>
      {(node.children ?? []).map((child) => (
        <CodeNodeItem key={child.code} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

// ── Esei Aras rubric panel ────────────────────────────────────────────────────

const ARAS_ROWS = [
  {
    aras: 4,
    range: '7–8m',
    descriptors: ['Pengetahuan & pemahaman sangat jelas', 'Bukti/contoh sangat sesuai', 'Membuat inferens yang tepat', 'Jawapan sangat mendalam/terperinci', 'Komunikasi/pengolahan sangat menarik', 'Menunjukkan kematangan'],
  },
  {
    aras: 3,
    range: '5–6m',
    descriptors: ['Pengetahuan & pemahaman sangat jelas', 'Bukti/contoh sangat sesuai', 'Membuat inferens', 'Jawapan mendalam', 'Komunikasi/pengolahan menarik'],
  },
  {
    aras: 2,
    range: '3–4m',
    descriptors: ['Pengetahuan & pemahaman jelas', 'Jawapan kurang mendalam', 'Menyatakan hujah secara ringkas'],
  },
  {
    aras: 1,
    range: '1–2m',
    descriptors: ['Pengetahuan & pemahaman terhad', 'Jawapan secara umum', 'Jawapan kurang mendalam', 'Menyatakan hujah secara ringkas'],
  },
];

function EseiCriteriaPanel({ maxMarks }: { maxMarks: number }) {
  return (
    <div>
      <h3 className="font-semibold text-[#111827] mb-3">Rubrik Penilaian KBAT</h3>
      <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-3 mb-4 text-sm">
        <AlertTriangle className="w-4 h-4 inline mr-1.5 mb-0.5" />
        Jawapan <strong>mesti dalam bentuk karangan (prosa berterusan)</strong>. Jawapan bentuk nota
        akan dihadkan kepada Aras 2 (maksimum 4 markah).
      </div>
      <div className="space-y-2">
        {ARAS_ROWS.map((row) => (
          <div key={row.aras} className="border border-[#E5E7EB] rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-bold bg-[#1E3A8A] text-white px-2 py-0.5 rounded">
                Aras {row.aras}
              </span>
              <span className="text-xs text-[#6B7280]">{row.range}</span>
            </div>
            <ul className="text-xs text-[#374151] space-y-0.5 list-disc pl-4">
              {row.descriptors.map((d, i) => (
                <li key={i}>{d}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="text-xs text-[#9CA3AF] mt-3">Markah maksimum: {maxMarks}</p>
    </div>
  );
}
