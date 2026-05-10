import { useEffect, useState } from 'react';
import { Search, Grid as GridIcon, List, Bookmark, BookmarkCheck, BookOpen, Clock } from 'lucide-react';
import { AppSidebar } from '../components/AppSidebar';
import { Input } from '../components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { StatusBadge } from '../components/StatusBadge';
import { Progress } from '../components/ui/progress';
import { Button } from '../components/ui/button';
import { api, TopicSummary, Chapter, APIError } from '../lib/api';

interface TopicsBrowserProps {
  onNavigate: (page: any, params?: any) => void;
}

// The existing TopicCard expects this shape — we adapt API data to it.
type UITopic = {
  id: string;
  title: string;
  chapter: string;          // "Bab N"
  chapterName: string;
  progress: number;         // 0 or 100 (we only know completed/not)
  status: 'completed' | 'in-progress' | 'not-started';
  duration: string;
  isBookmarked: boolean;
};

function toUITopic(t: TopicSummary): UITopic {
  return {
    id: String(t.topicId),
    title: t.topicName,
    chapter: `Bab ${t.chapterId}`,
    chapterName: t.chapterName,
    progress: t.isCompleted ? 100 : 0,
    status: t.isCompleted ? 'completed' : 'not-started',
    duration: t.estimatedDurationMinutes
      ? `${t.estimatedDurationMinutes} min`
      : '—',
    isBookmarked: t.isBookmarked,
  };
}

export function TopicsBrowser({ onNavigate }: TopicsBrowserProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedForm, setSelectedForm] = useState<'4' | '5'>('4');
  const [chapterFilter, setChapterFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const [topics, setTopics] = useState<UITopic[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch chapters when the form level changes
  useEffect(() => {
    api.listChapters(parseInt(selectedForm, 10))
      .then(setChapters)
      .catch(() => setChapters([]));
    setChapterFilter('all');
  }, [selectedForm]);

  // Fetch topics whenever form / chapter / search changes
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    api
      .listTopics({
        formLevel: parseInt(selectedForm, 10),
        chapterId: chapterFilter === 'all' ? undefined : parseInt(chapterFilter, 10),
        search: searchQuery.trim() || undefined,
      })
      .then((data) => {
        if (!cancelled) setTopics(data.map(toUITopic));
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof APIError ? err.message : 'Failed to load topics.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedForm, chapterFilter, searchQuery]);

  const filteredTopics = topics.filter((t) => {
    if (statusFilter === 'all') return true;
    return t.status === statusFilter;
  });

  const toggleBookmark = async (topicId: string) => {
    // Optimistic update
    const next = topics.map((t) =>
      t.id === topicId ? { ...t, isBookmarked: !t.isBookmarked } : t
    );
    setTopics(next);
    const target = next.find((t) => t.id === topicId);
    try {
      if (target?.isBookmarked) {
        await api.bookmark(parseInt(topicId, 10));
      } else {
        await api.unbookmark(parseInt(topicId, 10));
      }
    } catch {
      // Revert on failure
      setTopics(topics);
    }
  };

  const TopicCard = ({ topic }: { topic: UITopic }) => (
    <div className="bg-white rounded-xl shadow-edu-sm hover:shadow-edu-md transition-default overflow-hidden cursor-pointer group">
      <div className="relative">
        <div
          className="h-32 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center"
          onClick={() => onNavigate('topic-content', { topicId: topic.id })}
        >
          <BookOpen className="w-12 h-12 text-white opacity-80" />
        </div>
        <div className="absolute top-3 left-3">
          <span className="px-2 py-1 bg-white/90 backdrop-blur-sm text-xs font-medium text-[#1E3A8A] rounded">
            {topic.chapter}
          </span>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleBookmark(topic.id);
          }}
          className="absolute top-3 right-3 w-8 h-8 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center hover:bg-white transition-default"
        >
          {topic.isBookmarked ? (
            <BookmarkCheck className="w-4 h-4 text-[#F59E0B]" fill="#F59E0B" />
          ) : (
            <Bookmark className="w-4 h-4 text-[#6B7280]" />
          )}
        </button>
      </div>
      <div
        className="p-4"
        onClick={() => onNavigate('topic-content', { topicId: topic.id })}
      >
        <h3 className="font-bold text-[#111827] mb-1 group-hover:text-[#1E3A8A] transition-default">
          {topic.title}
        </h3>
        <p className="text-xs text-[#6B7280] mb-3">{topic.chapterName}</p>
        <div className="mb-3">
          <div className="flex justify-between text-xs text-[#6B7280] mb-1.5">
            <span>Progress</span>
            <span>{topic.progress}%</span>
          </div>
          <Progress value={topic.progress} className="h-1.5" />
        </div>
        <div className="flex items-center justify-between">
          <StatusBadge status={topic.status} />
          <span className="text-xs text-[#6B7280] flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {topic.duration}
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="topics" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-[#111827] mb-1">Topics</h1>
              <p className="text-[#6B7280]">Explore KSSM Sejarah syllabus topics</p>
            </div>
            <div className="relative w-80">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
              <Input
                type="search"
                placeholder="Search topics..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#F3F4F6] border-none"
              />
            </div>
          </div>
        </div>

        <div className="p-8">
          {/* Form-level tabs */}
          <Tabs value={selectedForm} onValueChange={(v) => setSelectedForm(v as '4' | '5')}>
            <TabsList className="mb-6">
              <TabsTrigger value="4">Form 4</TabsTrigger>
              <TabsTrigger value="5">Form 5</TabsTrigger>
            </TabsList>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <Select value={chapterFilter} onValueChange={setChapterFilter}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="All chapters" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All chapters</SelectItem>
                  {chapters.map((c) => (
                    <SelectItem key={c.chapterId} value={String(c.chapterId)}>
                      Bab {c.chapterId}: {c.chapterName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="not-started">Not started</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                </SelectContent>
              </Select>

              <div className="ml-auto flex gap-1 bg-white p-1 rounded-lg border border-[#E5E7EB]">
                <Button
                  size="sm"
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  onClick={() => setViewMode('grid')}
                  className="h-8"
                >
                  <GridIcon className="w-4 h-4" />
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  onClick={() => setViewMode('list')}
                  className="h-8"
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {/* Results */}
            {isLoading ? (
              <div className="text-center py-16 text-[#6B7280]">Loading topics…</div>
            ) : error ? (
              <div className="p-6 rounded-lg bg-[#FEE2E2] border border-[#DC2626]/20 text-[#991B1B]">
                {error}
              </div>
            ) : filteredTopics.length === 0 ? (
              <div className="text-center py-16">
                <BookOpen className="w-12 h-12 text-[#9CA3AF] mx-auto mb-3" />
                <p className="text-[#6B7280]">No topics match your filters.</p>
              </div>
            ) : (
              <div
                className={
                  viewMode === 'grid'
                    ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5'
                    : 'space-y-3'
                }
              >
                {filteredTopics.map((t) => (
                  <TopicCard key={t.id} topic={t} />
                ))}
              </div>
            )}
          </Tabs>
        </div>
      </div>
    </div>
  );
}
