import { useState } from 'react';
import { Mail, ArrowLeft, Check } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

interface ForgotPasswordProps {
  onNavigate: (page: any) => void;
}

export function ForgotPassword({ onNavigate }: ForgotPasswordProps) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validateEmail = (email: string) => {
    return /\S+@\S+\.\S+/.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      setError('Email is required');
      return;
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email');
      return;
    }

    setIsLoading(true);
    setError('');

    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      setIsSuccess(true);
    }, 1500);
  };

  const handleResend = () => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
    }, 1000);
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Logo and App Name */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-edu-lg">
              <span className="text-2xl font-bold text-[#1E3A8A]">EA</span>
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">EduAI</h1>
          </div>

          {/* Success Card */}
          <div className="bg-white rounded-2xl shadow-edu-xl p-8 text-center">
            <div className="w-20 h-20 bg-[#D1FAE5] rounded-full flex items-center justify-center mx-auto mb-6">
              <Mail className="w-10 h-10 text-[#059669]" />
            </div>

            <h2 className="text-2xl font-bold text-[#111827] mb-3">Check your inbox</h2>
            <p className="text-[#6B7280] mb-6">
              We've sent password reset instructions to
            </p>
            <p className="text-[#1E3A8A] font-medium mb-8">{email}</p>

            <div className="space-y-3">
              <Button
                onClick={() => onNavigate('login')}
                className="w-full h-12 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white font-medium rounded-lg"
              >
                Back to Login
              </Button>

              <p className="text-sm text-[#6B7280]">
                Didn't receive the email?{' '}
                <button
                  onClick={handleResend}
                  disabled={isLoading}
                  className="text-[#1E3A8A] hover:text-[#1E40AF] font-medium"
                >
                  {isLoading ? 'Sending...' : 'Resend email'}
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and App Name */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-edu-lg">
            <span className="text-2xl font-bold text-[#1E3A8A]">EA</span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">EduAI</h1>
        </div>

        {/* Reset Password Card */}
        <div className="bg-white rounded-2xl shadow-edu-xl p-8">
          <button
            onClick={() => onNavigate('login')}
            className="flex items-center gap-2 text-[#6B7280] hover:text-[#374151] mb-6 transition-default"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Back to login</span>
          </button>

          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-[#EFF6FF] rounded-full flex items-center justify-center mx-auto mb-4">
              <Mail className="w-8 h-8 text-[#1E3A8A]" />
            </div>
            <h2 className="text-2xl font-bold text-[#111827] mb-2">Reset Password</h2>
            <p className="text-[#6B7280]">
              Enter your email and we'll send you reset instructions
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[#374151] mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError('');
                  }}
                  placeholder="your.email@student.edu.my"
                  className={`pl-12 h-11 ${error ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''}`}
                />
              </div>
              {error && <p className="text-xs text-[#DC2626] mt-1">{error}</p>}
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white font-medium rounded-lg shadow-edu-md"
            >
              {isLoading ? 'Sending...' : 'Send Reset Instructions'}
            </Button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-blue-100 mt-6">
          © 2026 EduAI. Aligned with KSSM Sejarah.
        </p>
      </div>
    </div>
  );
}
