import {
  Home,
  BookOpen,
  Bot,
  ClipboardList,
  PencilLine,
  TrendingUp,
  Bookmark,
  Settings,
  ChevronLeft,
  ChevronRight,
  User,
  LogOut,
} from 'lucide-react';
import { useState } from 'react';

interface AppSidebarProps {
  currentPage: string;
  onNavigate: (page: any) => void;
  onLogout?: () => void;
  userName?: string;
  userEmail?: string;
}

export function AppSidebar({
  currentPage,
  onNavigate,
  onLogout,
  userName = 'Iusupov Alimzhan',
  userEmail = '1231301318@student.mmu.edu.my',
}: AppSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'topics', label: 'Topics', icon: BookOpen },
    { id: 'ai-tutor', label: 'AI Tutor', icon: Bot },
    { id: 'quiz-selection', label: 'Quizzes', icon: ClipboardList },
    { id: 'essay-practice', label: 'Essay Practice', icon: PencilLine },
    { id: 'progress', label: 'My Progress', icon: TrendingUp },
    { id: 'bookmarks', label: 'Bookmarks', icon: Bookmark },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div
      className={`${
        isCollapsed ? 'w-[72px]' : 'w-[280px]'
      } bg-white border-r border-[#E5E7EB] flex flex-col transition-all duration-200 relative`}
    >
      {/* Logo Section */}
      <div className="p-6 border-b border-[#E5E7EB]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-xl flex items-center justify-center flex-shrink-0">
            <span className="text-lg font-bold text-white">EA</span>
          </div>
          {!isCollapsed && (
            <div>
              <h1 className="text-xl font-bold text-[#111827]">EduAI</h1>
              <p className="text-xs text-[#6B7280]">SPM Sejarah</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 py-4 px-3 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center gap-3 px-4 h-12 rounded-lg mb-1 transition-default ${
                isActive
                  ? 'bg-[#EFF6FF] text-[#1E3A8A] border-l-4 border-[#1E3A8A]'
                  : 'text-[#6B7280] hover:bg-[#F3F4F6] hover:text-[#374151]'
              }`}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="font-medium text-sm">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* User Profile Section */}
      <div className="border-t border-[#E5E7EB] p-3">
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg hover:bg-[#F3F4F6] transition-default ${
              isCollapsed ? 'justify-center' : ''
            }`}
          >
            <div className="w-10 h-10 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-full flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-white" />
            </div>
            {!isCollapsed && (
              <div className="flex-1 text-left">
                <p className="text-sm font-medium text-[#111827] truncate">{userName}</p>
                <p className="text-xs text-[#6B7280] truncate">{userEmail}</p>
              </div>
            )}
          </button>

          {/* User Dropdown Menu */}
          {showUserMenu && !isCollapsed && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-[#E5E7EB] rounded-lg shadow-edu-lg overflow-hidden">
              <button
                onClick={() => {
                  setShowUserMenu(false);
                  onNavigate('settings');
                }}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#F3F4F6] transition-default text-left"
              >
                <Settings className="w-4 h-4 text-[#6B7280]" />
                <span className="text-sm text-[#374151]">Settings</span>
              </button>
              <button
                onClick={() => {
                  setShowUserMenu(false);
                  onLogout?.();
                }}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#FEE2E2] transition-default text-left border-t border-[#E5E7EB]"
              >
                <LogOut className="w-4 h-4 text-[#DC2626]" />
                <span className="text-sm text-[#DC2626]">Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Collapse Toggle Button */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-20 w-6 h-6 bg-white border border-[#E5E7EB] rounded-full flex items-center justify-center shadow-edu-md hover:bg-[#F3F4F6] transition-default"
      >
        {isCollapsed ? (
          <ChevronRight className="w-4 h-4 text-[#6B7280]" />
        ) : (
          <ChevronLeft className="w-4 h-4 text-[#6B7280]" />
        )}
      </button>
    </div>
  );
}