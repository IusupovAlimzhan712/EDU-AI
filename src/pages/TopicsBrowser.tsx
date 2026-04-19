import { useState } from 'react';
import { Search, Grid as GridIcon, List, Bookmark, BookmarkCheck, BookOpen, Clock } from 'lucide-react';
import { AppSidebar } from '../components/AppSidebar';
import { Input } from '../components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { StatusBadge } from '../components/StatusBadge';
import { Progress } from '../components/ui/progress';
import { Button } from '../components/ui/button';

interface TopicsBrowserProps {
  onNavigate: (page: any, params?: any) => void;
}

const form4Chapters = [
  { id: 'bab1', name: 'Bab 1: Kemunculan Tamadun Awal Manusia' },
  { id: 'bab2', name: 'Bab 2: Peningkatan Tamadun' },
  { id: 'bab3', name: 'Bab 3: Tamadun Awal Asia Tenggara' },
  { id: 'bab4', name: 'Bab 4: Kemunculan Tamadun Islam dan Perkembangannya di Makkah' },
  { id: 'bab5', name: 'Bab 5: Kerajaan Islam di Madinah' },
  { id: 'bab6', name: 'Bab 6: Kerajaan Alam Melayu' },
  { id: 'bab7', name: 'Bab 7: Islam di Asia Tenggara' },
];

const form5Chapters = [
  { id: 'bab1', name: 'Bab 1: Warisan Negara Bangsa' },
  { id: 'bab2', name: 'Bab 2: Kebangkitan Nasionalisme' },
  { id: 'bab3', name: 'Bab 3: Kemerdekaan Tanah Melayu' },
  { id: 'bab4', name: 'Bab 4: Penubuhan Malaysia' },
  { id: 'bab5', name: 'Bab 5: Pembangunan Negara' },
  { id: 'bab6', name: 'Bab 6: Pengukuhan Negara Bangsa' },
  { id: 'bab7', name: 'Bab 7: Malaysia dalam Konteks Global' },
];

const form4Topics = [
  {
    id: '1',
    title: 'Zaman Prasejarah',
    chapter: 'Bab 1',
    chapterName: 'Kemunculan Tamadun Awal Manusia',
    progress: 100,
    status: 'completed' as const,
    duration: '15 min',
    isBookmarked: true,
  },
  {
    id: '2',
    title: 'Zaman Neolitik',
    chapter: 'Bab 1',
    chapterName: 'Kemunculan Tamadun Awal Manusia',
    progress: 65,
    status: 'in-progress' as const,
    duration: '12 min',
    isBookmarked: false,
  },
  {
    id: '3',
    title: 'Tamadun Mesopotamia',
    chapter: 'Bab 2',
    chapterName: 'Peningkatan Tamadun',
    progress: 0,
    status: 'not-started' as const,
    duration: '18 min',
    isBookmarked: false,
  },
  {
    id: '4',
    title: 'Tamadun Mesir Purba',
    chapter: 'Bab 2',
    chapterName: 'Peningkatan Tamadun',
    progress: 30,
    status: 'in-progress' as const,
    duration: '20 min',
    isBookmarked: true,
  },
  {
    id: '5',
    title: 'Kesultanan Melayu Melaka',
    chapter: 'Bab 6',
    chapterName: 'Kerajaan Alam Melayu',
    progress: 100,
    status: 'completed' as const,
    duration: '25 min',
    isBookmarked: true,
  },
  {
    id: '6',
    title: 'Penyebaran Islam di Nusantara',
    chapter: 'Bab 7',
    chapterName: 'Islam di Asia Tenggara',
    progress: 0,
    status: 'not-started' as const,
    duration: '22 min',
    isBookmarked: false,
  },
];

const form5Topics = [
  {
    id: '7',
    title: 'Pendudukan Jepun di Tanah Melayu',
    chapter: 'Bab 1',
    chapterName: 'Warisan Negara Bangsa',
    progress: 45,
    status: 'in-progress' as const,
    duration: '20 min',
    isBookmarked: false,
  },
  {
    id: '8',
    title: 'Kemunculan Nasionalisme',
    chapter: 'Bab 2',
    chapterName: 'Kebangkitan Nasionalisme',
    progress: 0,
    status: 'not-started' as const,
    duration: '18 min',
    isBookmarked: false,
  },
  {
    id: '9',
    title: 'Perjuangan Menuntut Kemerdekaan',
    chapter: 'Bab 3',
    chapterName: 'Kemerdekaan Tanah Melayu',
    progress: 80,
    status: 'in-progress' as const,
    duration: '25 min',
    isBookmarked: true,
  },
  {
    id: '10',
    title: 'Pembentukan Malaysia',
    chapter: 'Bab 4',
    chapterName: 'Penubuhan Malaysia',
    progress: 100,
    status: 'completed' as const,
    duration: '22 min',
    isBookmarked: false,
  },
];

export function TopicsBrowser({ onNavigate }: TopicsBrowserProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedForm, setSelectedForm] = useState('4');
  const [chapterFilter, setChapterFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [bookmarkedTopics, setBookmarkedTopics] = useState<Set<string>>(
    new Set(['1', '4', '5', '9'])
  );

  const topics = selectedForm === '4' ? form4Topics : form5Topics;
  const chapters = selectedForm === '4' ? form4Chapters : form5Chapters;

  const filteredTopics = topics.filter((topic) => {
    const matchesSearch = topic.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesChapter = chapterFilter === 'all' || topic.chapter === chapterFilter;
    const matchesStatus = statusFilter === 'all' || topic.status === statusFilter;
    return matchesSearch && matchesChapter && matchesStatus;
  });

  const toggleBookmark = (topicId: string) => {
    const newBookmarks = new Set(bookmarkedTopics);
    if (newBookmarks.has(topicId)) {
      newBookmarks.delete(topicId);
    } else {
      newBookmarks.add(topicId);
    }
    setBookmarkedTopics(newBookmarks);
  };

  const TopicCard = ({ topic }: { topic: typeof topics[0] }) => (
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
          {bookmarkedTopics.has(topic.id) ? (
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
        {/* Header */}
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

        {/* Main Content */}
        <div className="p-8 max-w-7xl">
          {/* Form Level Tabs */}
          <Tabs value={selectedForm} onValueChange={setSelectedForm} className="mb-6">
            <TabsList className="bg-white border border-[#E5E7EB]">
              <TabsTrigger value="4" className="gap-2">
                Form 4
                <span className="px-2 py-0.5 bg-[#DBEAFE] text-[#1E3A8A] text-xs rounded-full">
                  {form4Topics.length}
                </span>
              </TabsTrigger>
              <TabsTrigger value="5" className="gap-2">
                Form 5
                <span className="px-2 py-0.5 bg-[#E0E7FF] text-[#4338CA] text-xs rounded-full">
                  {form5Topics.length}
                </span>
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Filters Bar */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[#374151]">Chapter:</span>
                <Select value={chapterFilter} onValueChange={setChapterFilter}>
                  <SelectTrigger className="w-[200px] bg-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Chapters</SelectItem>
                    {chapters.map((chapter) => (
                      <SelectItem key={chapter.id} value={chapter.id}>
                        {chapter.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[#374151]">Status:</span>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[180px] bg-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="in-progress">In Progress</SelectItem>
                    <SelectItem value="not-started">Not Started</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-white border border-[#E5E7EB] rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded transition-default ${
                  viewMode === 'grid'
                    ? 'bg-[#EFF6FF] text-[#1E3A8A]'
                    : 'text-[#6B7280] hover:text-[#374151]'
                }`}
              >
                <GridIcon className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded transition-default ${
                  viewMode === 'list'
                    ? 'bg-[#EFF6FF] text-[#1E3A8A]'
                    : 'text-[#6B7280] hover:text-[#374151]'
                }`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Topics Grid */}
          {filteredTopics.length > 0 ? (
            <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-4'}>
              {filteredTopics.map((topic) => (
                <TopicCard key={topic.id} topic={topic} />
              ))}
            </div>
          ) : (
            <div className="text-center py-16">
              <BookOpen className="w-16 h-16 text-[#D1D5DB] mx-auto mb-4" />
              <h3 className="text-lg font-bold text-[#111827] mb-2">No topics found</h3>
              <p className="text-[#6B7280] mb-4">Try adjusting your filters</p>
              <Button
                onClick={() => {
                  setSearchQuery('');
                  setChapterFilter('all');
                  setStatusFilter('all');
                }}
                variant="outline"
              >
                Clear Filters
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
