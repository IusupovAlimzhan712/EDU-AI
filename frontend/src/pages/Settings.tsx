import { useEffect, useState } from 'react';
import { AppSidebar } from '../components/AppSidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { User, Shield, Bell, BookOpen, Download, Trash2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api, APIError } from '../lib/api';

interface SettingsProps {
  onNavigate: (page: any) => void;
  onLogout?: () => void;
}

export function Settings({ onNavigate, onLogout }: SettingsProps) {
  const { student, refreshProfile } = useAuth();
  const [profile, setProfile] = useState({
    fullName: student?.fullName ?? '',
    email: student?.email ?? '',
    formLevel: student?.formLevel ? String(student.formLevel) : '4',
  });

  // Keep local form in sync once /me resolves
  useEffect(() => {
    if (student) {
      setProfile({
        fullName: student.fullName,
        email: student.email,
        formLevel: String(student.formLevel),
      });
      setPrefs({
        quizDifficulty: student.quizDifficulty ?? 'medium',
        questionsPerQuiz: String(student.questionsPerQuiz ?? 10),
      });
    }
  }, [student]);

  const [prefs, setPrefs] = useState({
    quizDifficulty: (student?.quizDifficulty ?? 'medium') as 'easy' | 'medium' | 'hard',
    questionsPerQuiz: String(student?.questionsPerQuiz ?? 10),
  });
  const [prefsBanner, setPrefsBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [prefsSaving, setPrefsSaving] = useState(false);

  // Banner state for inline feedback
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Change-password modal state
  const [showPwdForm, setShowPwdForm] = useState(false);
  const [pwdForm, setPwdForm] = useState({ current: '', next: '', confirm: '' });
  const [pwdError, setPwdError] = useState<string | null>(null);
  const [pwdSaving, setPwdSaving] = useState(false);

  const handleSaveProfile = async () => {
    setBanner(null);
    setIsSaving(true);
    try {
      await api.updateMe({
        fullName: profile.fullName,
        formLevel: parseInt(profile.formLevel, 10),
      });
      await refreshProfile();
      setBanner({ type: 'success', message: 'Profile updated successfully.' });
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : 'Failed to update profile.';
      setBanner({ type: 'error', message });
    } finally {
      setIsSaving(false);
    }
  };

  const savePreferences = async (newPrefs: { quizDifficulty: 'easy' | 'medium' | 'hard'; questionsPerQuiz: string }) => {
    setPrefsBanner(null);
    setPrefsSaving(true);
    try {
      await api.updateMe({
        quizDifficulty: newPrefs.quizDifficulty,
        questionsPerQuiz: parseInt(newPrefs.questionsPerQuiz, 10),
      });
      await refreshProfile();
      setPrefsBanner({ type: 'success', message: 'Saved.' });
    } catch (err) {
      const message =
        err instanceof APIError ? err.message : 'Failed to save preferences.';
      setPrefsBanner({ type: 'error', message });
    } finally {
      setPrefsSaving(false);
    }
  };

  const handleSavePreferences = () => savePreferences(prefs);

  const handleChangePassword = () => {
    setShowPwdForm(true);
    setPwdError(null);
    setPwdForm({ current: '', next: '', confirm: '' });
  };

  const handleSubmitPasswordChange = async () => {
    setPwdError(null);
    if (pwdForm.next !== pwdForm.confirm) {
      setPwdError('New password and confirmation do not match.');
      return;
    }
    setPwdSaving(true);
    try {
      await api.changePassword(pwdForm.current, pwdForm.next);
      // Backend invalidates all sessions on password change → log out.
      setShowPwdForm(false);
      if (onLogout) onLogout();
    } catch (err) {
      setPwdError(
        err instanceof APIError ? err.message : 'Failed to change password.'
      );
    } finally {
      setPwdSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      return;
    }
    try {
      await api.deleteMe();
      if (onLogout) onLogout();
    } catch (err) {
      setBanner({
        type: 'error',
        message: err instanceof APIError ? err.message : 'Failed to delete account.',
      });
    }
  };

  return (
    <div className="flex h-screen bg-[#F9FAFB]">
      <AppSidebar currentPage="settings" onNavigate={onNavigate} onLogout={onLogout} />

      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
          <h1 className="text-2xl font-bold text-[#111827]">Settings</h1>
          <p className="text-[#6B7280]">Manage your account and preferences</p>
        </div>

        {/* Main Content */}
        <div className="p-8 max-w-4xl">
          {/* Profile Section */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-[#DBEAFE] rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-[#1E3A8A]" />
              </div>
              <h2 className="text-xl font-bold text-[#111827]">Profile</h2>
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] rounded-full flex items-center justify-center">
                  <User className="w-10 h-10 text-white" />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#374151] mb-2">
                  Full Name
                </label>
                <Input
                  value={profile.fullName}
                  onChange={(e) => setProfile({ ...profile, fullName: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#374151] mb-2">
                  Email
                </label>
                <div className="relative">
                  <Input
                    value={profile.email}
                    disabled
                    className="pr-20"
                  />
                  <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-xs bg-[#D1FAE5] text-[#059669] px-2 py-1 rounded">
                    Verified
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#374151] mb-2">
                  Form Level
                </label>
                <Select
                  value={profile.formLevel}
                  onValueChange={(value) => setProfile({ ...profile, formLevel: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="4">Form 4</SelectItem>
                    <SelectItem value="5">Form 5</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleSaveProfile}
                disabled={isSaving}
                className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
              >
                {isSaving ? 'Saving…' : 'Save Changes'}
              </Button>

              {banner && (
                <div
                  className={`mt-3 p-3 rounded-lg text-sm ${
                    banner.type === 'success'
                      ? 'bg-[#D1FAE5] text-[#065F46] border border-[#059669]/30'
                      : 'bg-[#FEE2E2] text-[#991B1B] border border-[#DC2626]/30'
                  }`}
                >
                  {banner.message}
                </div>
              )}
            </div>
          </div>

          {/* Notification Preferences */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-[#FEF3C7] rounded-full flex items-center justify-center">
                <Bell className="w-5 h-5 text-[#F59E0B]" />
              </div>
              <h2 className="text-xl font-bold text-[#111827]">Notification Preferences</h2>
            </div>

            <p className="text-sm text-[#6B7280]">
              Notification preferences <span className="text-[#9CA3AF]">(coming soon)</span>
            </p>
          </div>

          {/* Learning Preferences */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-[#EDE9FE] rounded-full flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-[#7C3AED]" />
              </div>
              <h2 className="text-xl font-bold text-[#111827]">Learning Preferences</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-2">
                  Default Quiz Difficulty
                </label>
                <Select
                  value={prefs.quizDifficulty}
                  onValueChange={(value) => {
                    const next = { ...prefs, quizDifficulty: value as 'easy' | 'medium' | 'hard' };
                    setPrefs(next);
                    savePreferences(next);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="easy">Easy</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="hard">Hard</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#374151] mb-2">
                  Questions per Quiz
                </label>
                <Select
                  value={prefs.questionsPerQuiz}
                  onValueChange={(value) => {
                    const next = { ...prefs, questionsPerQuiz: value };
                    setPrefs(next);
                    savePreferences(next);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">5 questions</SelectItem>
                    <SelectItem value="10">10 questions</SelectItem>
                    <SelectItem value="15">15 questions</SelectItem>
                    <SelectItem value="20">20 questions</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  onClick={handleSavePreferences}
                  disabled={prefsSaving}
                  className="bg-[#7C3AED] hover:bg-[#6D28D9] text-white"
                >
                  {prefsSaving ? 'Saving…' : 'Save Preferences'}
                </Button>
                {prefsBanner && (
                  <span
                    className={`text-sm ${
                      prefsBanner.type === 'success' ? 'text-[#059669]' : 'text-[#DC2626]'
                    }`}
                  >
                    {prefsBanner.message}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Account Section */}
          <div className="bg-white rounded-xl shadow-edu-sm p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-[#FEE2E2] rounded-full flex items-center justify-center">
                <Shield className="w-5 h-5 text-[#DC2626]" />
              </div>
              <h2 className="text-xl font-bold text-[#111827]">Account</h2>
            </div>

            <div className="space-y-3">
              <Button onClick={handleChangePassword} variant="outline" className="w-full justify-start">
                <Shield className="w-4 h-4 mr-2" />
                Change Password
              </Button>

              {showPwdForm && (
                <div className="p-4 rounded-lg bg-[#F9FAFB] border border-[#E5E7EB] space-y-3">
                  {pwdError && (
                    <div className="p-2 rounded bg-[#FEE2E2] border border-[#DC2626]/30 text-sm text-[#991B1B]">
                      {pwdError}
                    </div>
                  )}
                  <div>
                    <label className="block text-sm font-medium text-[#374151] mb-1">
                      Current Password
                    </label>
                    <Input
                      type="password"
                      value={pwdForm.current}
                      onChange={(e) => setPwdForm({ ...pwdForm, current: e.target.value })}
                      placeholder="Enter current password"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#374151] mb-1">
                      New Password
                    </label>
                    <Input
                      type="password"
                      value={pwdForm.next}
                      onChange={(e) => setPwdForm({ ...pwdForm, next: e.target.value })}
                      placeholder="At least 8 characters, mixed case + number"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#374151] mb-1">
                      Confirm New Password
                    </label>
                    <Input
                      type="password"
                      value={pwdForm.confirm}
                      onChange={(e) => setPwdForm({ ...pwdForm, confirm: e.target.value })}
                      placeholder="Re-enter new password"
                    />
                  </div>
                  <div className="flex gap-2 pt-1">
                    <Button
                      onClick={handleSubmitPasswordChange}
                      disabled={pwdSaving}
                      size="sm"
                      className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white"
                    >
                      {pwdSaving ? 'Saving…' : 'Update Password'}
                    </Button>
                    <Button onClick={() => setShowPwdForm(false)} size="sm" variant="outline">
                      Cancel
                    </Button>
                  </div>
                  <p className="text-xs text-[#6B7280]">
                    After changing your password you will be logged out and need to sign in again.
                  </p>
                </div>
              )}

              <Button variant="outline" className="w-full justify-start" disabled>
                <Download className="w-4 h-4 mr-2" />
                Download My Data <span className="ml-2 text-xs text-[#9CA3AF]">(coming soon)</span>
              </Button>

              <Button
                onClick={handleDeleteAccount}
                variant="outline"
                className="w-full justify-start text-[#DC2626] hover:bg-[#FEE2E2] border-[#DC2626]"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Account
              </Button>
            </div>
          </div>

          {/* About Section */}
          <div className="mt-6 p-6 border-t border-[#E5E7EB]">
            <p className="text-sm text-[#6B7280] text-center mb-2">
              EduAI v1.0.0 - AI Study Companion for SPM Students
            </p>
            <div className="flex justify-center gap-4 text-sm text-[#9CA3AF]">
              <span>Terms &amp; Conditions</span>
              <span>•</span>
              <span>Privacy Policy</span>
              <span>•</span>
              <span>Contact Support</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}