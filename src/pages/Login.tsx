import { useState } from 'react';
import { Mail, Lock, Eye, EyeOff } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Checkbox } from '../components/ui/checkbox';

interface LoginProps {
  onNavigate: (page: any) => void;
  onLogin: () => void;
}

export function Login({ onNavigate, onLogin }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [isLoading, setIsLoading] = useState(false);

  const validateForm = () => {
    const newErrors: { email?: string; password?: string } = {};

    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = 'Please enter a valid email';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      setIsLoading(false);
      onLogin();
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1E3A8A] to-[#3B82F6] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and App Name */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-edu-lg">
            <span className="text-2xl font-bold text-[#1E3A8A]">EA</span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">EduAI</h1>
          <p className="text-blue-100">AI Study Companion for SPM Students</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-edu-xl p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-[#111827] mb-2">Welcome back</h2>
            <p className="text-[#6B7280]">Sign in to continue your learning journey</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Input */}
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
                    if (errors.email) setErrors({ ...errors, email: undefined });
                  }}
                  placeholder="your.email@student.edu.my"
                  className={`pl-12 h-11 ${
                    errors.email ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''
                  }`}
                />
              </div>
              {errors.email && (
                <p className="text-xs text-[#DC2626] mt-1">{errors.email}</p>
              )}
            </div>

            {/* Password Input */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[#374151] mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errors.password) setErrors({ ...errors, password: undefined });
                  }}
                  placeholder="Enter your password"
                  className={`pl-12 pr-12 h-11 ${
                    errors.password ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-[#6B7280] hover:text-[#374151]"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-[#DC2626] mt-1">{errors.password}</p>
              )}
            </div>

            {/* Remember Me and Forgot Password */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="remember"
                  checked={rememberMe}
                  onCheckedChange={(checked) => setRememberMe(checked as boolean)}
                />
                <label htmlFor="remember" className="text-sm text-[#374151] cursor-pointer">
                  Remember me
                </label>
              </div>
              <button
                type="button"
                onClick={() => onNavigate('forgot-password')}
                className="text-sm text-[#1E3A8A] hover:text-[#1E40AF] font-medium"
              >
                Forgot Password?
              </button>
            </div>

            {/* Login Button */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white font-medium rounded-lg shadow-edu-md"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[#E5E7EB]"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-[#6B7280]">or</span>
              </div>
            </div>

            {/* Register Link */}
            <p className="text-center text-sm text-[#6B7280]">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => onNavigate('register')}
                className="text-[#1E3A8A] hover:text-[#1E40AF] font-medium"
              >
                Register
              </button>
            </p>
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
