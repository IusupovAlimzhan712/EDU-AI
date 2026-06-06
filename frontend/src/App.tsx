import { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { Dashboard } from './pages/Dashboard';
import { TopicsBrowser } from './pages/TopicsBrowser';
import { TopicContent } from './pages/TopicContent';
import { AITutor } from './pages/AITutor';
import { QuizSelection } from './pages/QuizSelection';
import { QuizInProgress } from './pages/QuizInProgress';
import { QuizResults } from './pages/QuizResults';
import { EssayPractice } from './pages/EssayPractice';
import { EssayWriting } from './pages/EssayWriting';
import { EssayFeedback } from './pages/EssayFeedback';
import { MyProgress } from './pages/MyProgress';
import { Bookmarks } from './pages/Bookmarks';
import { Settings } from './pages/Settings';

type Page =
  | 'login'
  | 'register'
  | 'forgot-password'
  | 'dashboard'
  | 'topics'
  | 'topic-content'
  | 'ai-tutor'
  | 'quiz-selection'
  | 'quiz-in-progress'
  | 'quiz-results'
  | 'essay-practice'
  | 'essay-writing'
  | 'essay-feedback'
  | 'progress'
  | 'bookmarks'
  | 'settings';

export default function App() {
  const { isAuthenticated, isInitializing, logout } = useAuth();
  const [currentPage, setCurrentPage] = useState<Page>('login');
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [selectedQuizId, setSelectedQuizId] = useState<string | null>(null);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [selectedEssayQuestionId, setSelectedEssayQuestionId] = useState<string | null>(null);
  const [selectedFormLevel, setSelectedFormLevel] = useState<string | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);

  // Once auth state is restored, jump straight to dashboard if logged in.
  useEffect(() => {
    if (!isInitializing && isAuthenticated && currentPage === 'login') {
      setCurrentPage('dashboard');
    }
  }, [isInitializing, isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  const navigate = (
    page: Page,
    params?: {
      topicId?: string;
      quizId?: string;
      questionId?: string;
      attemptId?: string | null;
      formLevel?: string;
      chapterId?: string;
    }
  ) => {
    if (params?.topicId) setSelectedTopicId(params.topicId);
    if (params?.quizId) setSelectedQuizId(params.quizId);
    if (params?.questionId) setSelectedEssayQuestionId(params.questionId);
    if (params?.attemptId !== undefined) setSelectedAttemptId(params.attemptId);
    // Chapter deep-link: set when provided, reset to null when navigating to
    // 'topics' without a chapter hint so stale state doesn't persist.
    if (page === 'topics') {
      setSelectedFormLevel(params?.formLevel ?? null);
      setSelectedChapterId(params?.chapterId ?? null);
    }
    setCurrentPage(page);
  };

  const handleLogin = () => navigate('dashboard');
  const handleLogout = async () => {
    await logout();
    navigate('login');
  };

  // Loading state while we check for a stored session
  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6]">
        <div className="text-white text-lg">Loading…</div>
      </div>
    );
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'login':
        return <Login onNavigate={navigate} onLogin={handleLogin} />;
      case 'register':
        return <Register onNavigate={navigate} onLogin={handleLogin} />;
      case 'forgot-password':
        return <ForgotPassword onNavigate={navigate} />;
      case 'dashboard':
        return <Dashboard onNavigate={navigate} />;
      case 'topics':
        return (
          <TopicsBrowser
            onNavigate={navigate}
            initialFormLevel={selectedFormLevel}
            initialChapterId={selectedChapterId}
          />
        );
      case 'topic-content':
        return <TopicContent onNavigate={navigate} topicId={selectedTopicId} />;
      case 'ai-tutor':
        return <AITutor onNavigate={navigate} />;
      case 'quiz-selection':
        return <QuizSelection onNavigate={navigate} />;
      case 'quiz-in-progress':
        return <QuizInProgress onNavigate={navigate} quizId={selectedQuizId} attemptId={selectedAttemptId} />;
      case 'quiz-results':
        return <QuizResults onNavigate={navigate} quizId={selectedQuizId} attemptId={selectedAttemptId} />;
      case 'essay-practice':
        return <EssayPractice onNavigate={navigate} />;
      case 'essay-writing':
        return <EssayWriting onNavigate={navigate} questionId={selectedEssayQuestionId} />;
      case 'essay-feedback':
        return <EssayFeedback onNavigate={navigate} attemptId={selectedAttemptId} />;
      case 'progress':
        return <MyProgress onNavigate={navigate} />;
      case 'bookmarks':
        return <Bookmarks onNavigate={navigate} />;
      case 'settings':
        return <Settings onNavigate={navigate} onLogout={handleLogout} />;
      default:
        return <Login onNavigate={navigate} onLogin={handleLogin} />;
    }
  };

  return <div className="min-h-screen">{renderPage()}</div>;
}
