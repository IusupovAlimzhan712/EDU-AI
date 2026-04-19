import { useState } from 'react';
import { Mail, Lock, User, Eye, EyeOff, Check, X } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Checkbox } from '../components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

interface RegisterProps {
  onNavigate: (page: any) => void;
}

export function Register({ onNavigate }: RegisterProps) {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    formLevel: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const getPasswordStrength = (password: string) => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;

    return strength;
  };

  const passwordStrength = getPasswordStrength(formData.password);
  const strengthLabels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const strengthColors = ['', '#DC2626', '#F59E0B', '#FCD34D', '#059669'];

  const passwordRequirements = [
    { label: '8+ characters', met: formData.password.length >= 8 },
    { label: 'Uppercase letter', met: /[A-Z]/.test(formData.password) },
    { label: 'Lowercase letter', met: /[a-z]/.test(formData.password) },
    { label: 'Number', met: /[0-9]/.test(formData.password) },
  ];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.fullName) {
      newErrors.fullName = 'Full name is required';
    }

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (passwordStrength < 3) {
      newErrors.password = 'Password is not strong enough';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (!formData.formLevel) {
      newErrors.formLevel = 'Please select your form level';
    }

    if (!agreedToTerms) {
      newErrors.terms = 'You must agree to the Terms & Conditions';
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
      onNavigate('login');
    }, 1500);
  };

  const updateField = (field: string, value: string) => {
    setFormData({ ...formData, [field]: value });
    if (errors[field]) {
      const newErrors = { ...errors };
      delete newErrors[field];
      setErrors(newErrors);
    }
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

        {/* Register Card */}
        <div className="bg-white rounded-2xl shadow-edu-xl p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-[#111827] mb-2">Create Account</h2>
            <p className="text-[#6B7280]">Start your SPM Sejarah journey today</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Full Name */}
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-[#374151] mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
                <Input
                  id="fullName"
                  type="text"
                  value={formData.fullName}
                  onChange={(e) => updateField('fullName', e.target.value)}
                  placeholder="Iusupov Alimzhan"
                  className={`pl-12 h-11 ${errors.fullName ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''}`}
                />
              </div>
              {errors.fullName && <p className="text-xs text-[#DC2626] mt-1">{errors.fullName}</p>}
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[#374151] mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => updateField('email', e.target.value)}
                  placeholder="your.email@student.edu.my"
                  className={`pl-12 h-11 ${errors.email ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''}`}
                />
              </div>
              {errors.email && <p className="text-xs text-[#DC2626] mt-1">{errors.email}</p>}
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[#374151] mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => updateField('password', e.target.value)}
                  placeholder="Create a strong password"
                  className={`pl-12 pr-12 h-11 ${errors.password ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-[#6B7280]"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>

              {/* Password Strength Indicator */}
              {formData.password && (
                <div className="mt-2">
                  <div className="h-1.5 bg-[#E5E7EB] rounded-full overflow-hidden">
                    <div
                      className="h-full transition-all duration-300"
                      style={{
                        width: `${(passwordStrength / 4) * 100}%`,
                        backgroundColor: strengthColors[passwordStrength],
                      }}
                    />
                  </div>
                  <p className="text-xs mt-1" style={{ color: strengthColors[passwordStrength] }}>
                    {strengthLabels[passwordStrength]}
                  </p>

                  {/* Requirements Checklist */}
                  <div className="mt-2 space-y-1">
                    {passwordRequirements.map((req, index) => (
                      <div key={index} className="flex items-center gap-2 text-xs">
                        {req.met ? (
                          <Check className="w-3 h-3 text-[#059669]" />
                        ) : (
                          <X className="w-3 h-3 text-[#DC2626]" />
                        )}
                        <span className={req.met ? 'text-[#059669]' : 'text-[#6B7280]'}>
                          {req.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {errors.password && <p className="text-xs text-[#DC2626] mt-1">{errors.password}</p>}
            </div>

            {/* Confirm Password */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-[#374151] mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-[#6B7280]" />
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={formData.confirmPassword}
                  onChange={(e) => updateField('confirmPassword', e.target.value)}
                  placeholder="Re-enter your password"
                  className={`pl-12 pr-12 h-11 ${errors.confirmPassword ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''}`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-[#6B7280]"
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="text-xs text-[#DC2626] mt-1">{errors.confirmPassword}</p>
              )}
            </div>

            {/* Form Level */}
            <div>
              <label htmlFor="formLevel" className="block text-sm font-medium text-[#374151] mb-2">
                Form Level
              </label>
              <Select value={formData.formLevel} onValueChange={(value) => updateField('formLevel', value)}>
                <SelectTrigger className={`h-11 ${errors.formLevel ? 'border-[#DC2626] bg-[#FEE2E2]/50' : ''}`}>
                  <SelectValue placeholder="Select your form level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="4">Form 4</SelectItem>
                  <SelectItem value="5">Form 5</SelectItem>
                </SelectContent>
              </Select>
              {errors.formLevel && <p className="text-xs text-[#DC2626] mt-1">{errors.formLevel}</p>}
            </div>

            {/* Terms and Conditions */}
            <div>
              <div className="flex items-start gap-2">
                <Checkbox
                  id="terms"
                  checked={agreedToTerms}
                  onCheckedChange={(checked) => {
                    setAgreedToTerms(checked as boolean);
                    if (errors.terms) {
                      const newErrors = { ...errors };
                      delete newErrors.terms;
                      setErrors(newErrors);
                    }
                  }}
                  className="mt-0.5"
                />
                <label htmlFor="terms" className="text-sm text-[#374151] cursor-pointer">
                  I agree to the{' '}
                  <span className="text-[#1E3A8A] hover:underline">Terms & Conditions</span>
                </label>
              </div>
              {errors.terms && <p className="text-xs text-[#DC2626] mt-1">{errors.terms}</p>}
            </div>

            {/* Register Button */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 bg-[#1E3A8A] hover:bg-[#1E40AF] text-white font-medium rounded-lg shadow-edu-md mt-2"
            >
              {isLoading ? 'Creating account...' : 'Create Account'}
            </Button>

            {/* Login Link */}
            <p className="text-center text-sm text-[#6B7280] mt-4">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => onNavigate('login')}
                className="text-[#1E3A8A] hover:text-[#1E40AF] font-medium"
              >
                Login
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