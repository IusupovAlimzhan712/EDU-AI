import { useState } from 'react';
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
  const [currentPage, setCurrentPage] = useState<Page>('login');
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [selectedQuizId, setSelectedQuizId] = useState<string | null>(null);
  const [selectedEssayId, setSelectedEssayId] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const navigate = (page: Page, params?: { topicId?: string; quizId?: string; essayId?: string }) => {
    if (params?.topicId) setSelectedTopicId(params.topicId);
    if (params?.quizId) setSelectedQuizId(params.quizId);
    if (params?.essayId) setSelectedEssayId(params.essayId);
    setCurrentPage(page);
  };

  const handleLogin = () => {
    setIsAuthenticated(true);
    navigate('dashboard');
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    navigate('login');
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'login':
        return <Login onNavigate={navigate} onLogin={handleLogin} />;
      case 'register':
        return <Register onNavigate={navigate} />;
      case 'forgot-password':
        return <ForgotPassword onNavigate={navigate} />;
      case 'dashboard':
        return <Dashboard onNavigate={navigate} />;
      case 'topics':
        return <TopicsBrowser onNavigate={navigate} />;
      case 'topic-content':
        return <TopicContent onNavigate={navigate} topicId={selectedTopicId} />;
      case 'ai-tutor':
        return <AITutor onNavigate={navigate} />;
      case 'quiz-selection':
        return <QuizSelection onNavigate={navigate} />;
      case 'quiz-in-progress':
        return <QuizInProgress onNavigate={navigate} quizId={selectedQuizId} />;
      case 'quiz-results':
        return <QuizResults onNavigate={navigate} quizId={selectedQuizId} />;
      case 'essay-practice':
        return <EssayPractice onNavigate={navigate} />;
      case 'essay-writing':
        return <EssayWriting onNavigate={navigate} essayId={selectedEssayId} />;
      case 'essay-feedback':
        return <EssayFeedback onNavigate={navigate} essayId={selectedEssayId} />;
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
