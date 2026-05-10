import { useEffect, useState } from 'react';
import { AppSidebar } from '../components/AppSidebar';
import { Input } from '../components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Search, BookOpen, HelpCircle, PencilLine, Trash2, ExternalLink } from 'lucide-react';
import { api, TopicSummary, APIError } from '../lib/api';

interface BookmarksProps {
  onNavigate: (page: any, params?: any) => void;
}

type TopicBookmark = TopicSummary & { bookmarkedAt?: string };

function timeAgo(iso?: string): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const day = 86_400_000;
  if (diff < day) return 'Today';
  if (diff < 2 * day) return 'Yesterday';
  if (diff < 7 * day) return `${Math.floor(diff / day)} days ago`;
  if (diff < 30 * day) return `${Math.floor(diff / (7 * day))} weeks ago`;
  return new Date(iso).toLocaleDateString();
}

export function Bookmarks({ onNavigate }: BookmarksProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTab, setSelectedTab] = useState('topic');
  const [bookmarks, setBookmarks] = useState<TopicBookmark[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBookmarks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const items = (await api.getBookmarks()) as unknown as TopicBookmark[];
      setBookmarks(items);
    } catch (err) {
      setError(
        err instanceof APIError ? err.message : 'Failed to load bookmarks.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadBookmarks();
  }, []);

  const filtered = bookmarks.filter((b) =>
    b.topicName.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleRemove = async (topicId: number) => {
    // optimistic
    const prev = bookmarks;
    setBookmarks(bookmarks.filter((b) => b.topicId !== topicId));
    try {
      await api.unbookmark(topicId);
    } catch {
      setBookmarks(prev);
    }
  };

  const handleOpen = (b: TopicBookmark) => {
    onNavigate('topic-content', { topicId: String(b.topicId) });
  };

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="bookmarks" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-[#111827] mb-1">Bookmarks</h1>
              <p className="text-[#6B7280]">
                <span className="font-bold text-[#111827]">{filtered.length}</span>{' '}
                saved {filtered.length === 1 ? 'item' : 'items'}
              </p>
            </div>
            <div className="relative w-80">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
              <Input
                type="search"
                placeholder="Search bookmarks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#F3F4F6] border-none"
              />
            </div>
          </div>
        </div>

        <div className="p-8 max-w-5xl">
          <Tabs value={selectedTab} onValueChange={setSelectedTab} className="mb-6">
            <TabsList className="bg-white border border-[#E5E7EB]">
              <TabsTrigger value="topic">
                Topics
                <span className="ml-2 px-2 py-0.5 bg-[#F3F4F6] text-[#6B7280] text-xs rounded-full">
                  {bookmarks.length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="quiz" disabled>
                Quizzes <span className="ml-2 text-xs text-[#9CA3AF]">(Phase 2)</span>
              </TabsTrigger>
              <TabsTrigger value="essay" disabled>
                Essays <span className="ml-2 text-xs text-[#9CA3AF]">(Phase 3)</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {isLoading ? (
            <div className="text-center py-16 text-[#6B7280]">Loading…</div>
          ) : error ? (
            <div className="p-6 rounded-lg bg-[#FEE2E2] border border-[#DC2626]/20 text-[#991B1B]">
              {error}
            </div>
          ) : filtered.length > 0 ? (
            <div className="space-y-4">
              {filtered.map((b) => (
                <div
                  key={b.topicId}
                  className="bg-white rounded-xl shadow-edu-sm hover:shadow-edu-md transition-default p-6"
                >
                  <div className="flex items-start gap-4">
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: '#DBEAFE' }}
                    >
                      <BookOpen className="w-6 h-6" style={{ color: '#1E3A8A' }} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-bold text-[#111827] mb-1">{b.topicName}</h3>
                          <p className="text-sm text-[#6B7280]">
                            Bab {b.chapterId} — Form {b.formLevel}
                            {b.chapterName ? ` • ${b.chapterName}` : ''}
                          </p>
                        </div>
                        <span className="text-xs text-[#6B7280]">{timeAgo(b.bookmarkedAt)}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-4">
                        <Button
                          onClick={() => handleOpen(b)}
                          size="sm"
                          className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
                        >
                          <ExternalLink className="w-4 h-4 mr-2" />
                          Open
                        </Button>
                        <Button
                          onClick={() => handleRemove(b.topicId)}
                          size="sm"
                          variant="outline"
                          className="text-[#DC2626] hover:bg-[#FEE2E2]"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Remove
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <BookOpen className="w-16 h-16 text-[#D1D5DB] mx-auto mb-4" />
              <h3 className="text-lg font-bold text-[#111827] mb-2">No bookmarks yet</h3>
              <p className="text-[#6B7280] mb-4">
                {searchQuery ? 'Try adjusting your search' : 'Save topics for quick access'}
              </p>
              {!searchQuery && (
                <Button onClick={() => onNavigate('topics')}>Browse Topics</Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
