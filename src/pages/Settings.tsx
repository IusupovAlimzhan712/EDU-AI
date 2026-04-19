import { useState } from 'react';
import { AppSidebar } from '../components/AppSidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { User, Mail, Shield, Bell, Palette, BookOpen, Download, Trash2 } from 'lucide-react';

interface SettingsProps {
  onNavigate: (page: any) => void;
  onLogout?: () => void;
}

export function Settings({ onNavigate, onLogout }: SettingsProps) {
  const [profile, setProfile] = useState({
    fullName: 'Iusupov Alimzhan',
    email: '1231301318@student.mmu.edu.my',
    formLevel: '4',
  });

  const [notifications, setNotifications] = useState({
    email: true,
    studyReminders: true,
  });

  const handleSaveProfile = () => {
    alert('Profile updated successfully!');
  };

  const handleChangePassword = () => {
    alert('Password change functionality would open a modal here');
  };

  const handleDeleteAccount = () => {
    if (window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      alert('Account deletion confirmed');
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
                <Button variant="outline" size="sm">
                  Change Avatar
                </Button>
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

              <Button onClick={handleSaveProfile} className="bg-[#1E3A8A] hover:bg-[#1E40AF] text-white">
                Save Changes
              </Button>
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

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-[#111827]">Email Notifications</p>
                  <p className="text-sm text-[#6B7280]">Receive updates about your progress</p>
                </div>
                <Switch
                  checked={notifications.email}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, email: checked })
                  }
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-[#111827]">Study Reminders</p>
                  <p className="text-sm text-[#6B7280]">Get reminded to study daily</p>
                </div>
                <Switch
                  checked={notifications.studyReminders}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, studyReminders: checked })
                  }
                />
              </div>
            </div>
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
                <Select defaultValue="medium">
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
                <Select defaultValue="10">
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

              <Button variant="outline" className="w-full justify-start">
                <Download className="w-4 h-4 mr-2" />
                Download My Data
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
            <div className="flex justify-center gap-4 text-sm">
              <button className="text-[#1E3A8A] hover:underline">Terms & Conditions</button>
              <span className="text-[#D1D5DB]">•</span>
              <button className="text-[#1E3A8A] hover:underline">Privacy Policy</button>
              <span className="text-[#D1D5DB]">•</span>
              <button className="text-[#1E3A8A] hover:underline">Contact Support</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}