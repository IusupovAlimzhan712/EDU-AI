import { useState } from 'react';
import { AppSidebar } from '../components/AppSidebar';
import { Input } from '../components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import { Search, BookOpen, HelpCircle, PencilLine, Trash2, ExternalLink } from 'lucide-react';

interface BookmarksProps {
  onNavigate: (page: any, params?: any) => void;
}

const bookmarks = [
  {
    id: '1',
    type: 'topic',
    title: 'Kesultanan Melayu Melaka',
    chapter: 'Bab 6 - Form 4',
    date: '2 days ago',
  },
  {
    id: '2',
    type: 'quiz',
    title: 'Tamadun Awal Manusia',
    chapter: 'Bab 1 - Form 4',
    date: '1 week ago',
  },
  {
    id: '3',
    type: 'topic',
    title: 'Pendudukan Jepun di Tanah Melayu',
    chapter: 'Bab 1 - Form 5',
    date: '1 week ago',
  },
  {
    id: '4',
    type: 'essay',
    title: 'Huraikan faktor-faktor kejatuhan Kesultanan Melayu Melaka',
    chapter: 'Form 4',
    date: '2 weeks ago',
  },
];

export function Bookmarks({ onNavigate }: BookmarksProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTab, setSelectedTab] = useState('all');

  const filteredBookmarks = bookmarks.filter((bookmark) => {
    const matchesSearch = bookmark.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTab = selectedTab === 'all' || bookmark.type === selectedTab;
    return matchesSearch && matchesTab;
  });

  const getIcon = (type: string) => {
    switch (type) {
      case 'topic':
        return BookOpen;
      case 'quiz':
        return HelpCircle;
      case 'essay':
        return PencilLine;
      default:
        return BookOpen;
    }
  };

  const getIconColor = (type: string) => {
    switch (type) {
      case 'topic':
        return { bg: '#DBEAFE', color: '#1E3A8A' };
      case 'quiz':
        return { bg: '#FEF3C7', color: '#F59E0B' };
      case 'essay':
        return { bg: '#EDE9FE', color: '#7C3AED' };
      default:
        return { bg: '#F3F4F6', color: '#6B7280' };
    }
  };

  const handleOpen = (bookmark: typeof bookmarks[0]) => {
    switch (bookmark.type) {
      case 'topic':
        onNavigate('topic-content', { topicId: bookmark.id });
        break;
      case 'quiz':
        onNavigate('quiz-in-progress', { quizId: bookmark.id });
        break;
      case 'essay':
        onNavigate('essay-writing', { essayId: bookmark.id });
        break;
    }
  };

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="bookmarks" onNavigate={onNavigate} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-[#111827] mb-1">Bookmarks</h1>
              <p className="text-[#6B7280]">
                <span className="font-bold text-[#111827]">{filteredBookmarks.length}</span> saved items
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

        {/* Main Content */}
        <div className="p-8 max-w-5xl">
          {/* Tabs */}
          <Tabs value={selectedTab} onValueChange={setSelectedTab} className="mb-6">
            <TabsList className="bg-white border border-[#E5E7EB]">
              <TabsTrigger value="all">
                All
                <span className="ml-2 px-2 py-0.5 bg-[#F3F4F6] text-[#6B7280] text-xs rounded-full">
                  {bookmarks.length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="topic">
                Topics
                <span className="ml-2 px-2 py-0.5 bg-[#F3F4F6] text-[#6B7280] text-xs rounded-full">
                  {bookmarks.filter((b) => b.type === 'topic').length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="quiz">
                Quizzes
                <span className="ml-2 px-2 py-0.5 bg-[#F3F4F6] text-[#6B7280] text-xs rounded-full">
                  {bookmarks.filter((b) => b.type === 'quiz').length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="essay">
                Essays
                <span className="ml-2 px-2 py-0.5 bg-[#F3F4F6] text-[#6B7280] text-xs rounded-full">
                  {bookmarks.filter((b) => b.type === 'essay').length}
                </span>
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Bookmarks List */}
          {filteredBookmarks.length > 0 ? (
            <div className="space-y-4">
              {filteredBookmarks.map((bookmark) => {
                const Icon = getIcon(bookmark.type);
                const colors = getIconColor(bookmark.type);

                return (
                  <div
                    key={bookmark.id}
                    className="bg-white rounded-xl shadow-edu-sm hover:shadow-edu-md transition-default p-6"
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: colors.bg }}
                      >
                        <Icon className="w-6 h-6" style={{ color: colors.color }} />
                      </div>

                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h3 className="font-bold text-[#111827] mb-1">{bookmark.title}</h3>
                            <p className="text-sm text-[#6B7280]">{bookmark.chapter}</p>
                          </div>
                          <span className="text-xs text-[#6B7280]">{bookmark.date}</span>
                        </div>

                        <div className="flex items-center gap-2 mt-4">
                          <Button
                            onClick={() => handleOpen(bookmark)}
                            size="sm"
                            className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
                          >
                            <ExternalLink className="w-4 h-4 mr-2" />
                            Open
                          </Button>
                          <Button size="sm" variant="outline" className="text-[#DC2626] hover:bg-[#FEE2E2]">
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-16">
              <BookOpen className="w-16 h-16 text-[#D1D5DB] mx-auto mb-4" />
              <h3 className="text-lg font-bold text-[#111827] mb-2">No bookmarks found</h3>
              <p className="text-[#6B7280] mb-4">
                {searchQuery
                  ? 'Try adjusting your search'
                  : 'Save topics and questions for quick access'}
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
