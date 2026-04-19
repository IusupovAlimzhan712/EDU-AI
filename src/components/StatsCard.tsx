import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
  icon: LucideIcon;
  iconColor: string;
  iconBgColor: string;
  label: string;
  value: string | number;
  trend?: {
    direction: 'up' | 'down';
    value: string;
  };
  className?: string;
}

export function StatsCard({
  icon: Icon,
  iconColor,
  iconBgColor,
  label,
  value,
  trend,
  className = '',
}: StatsCardProps) {
  return (
    <div className={`bg-white rounded-xl p-6 shadow-edu-sm transition-default hover:shadow-edu-md ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-[#6B7280] mb-1">{label}</p>
          <p className="text-2xl font-bold text-[#111827]">{value}</p>
          {trend && (
            <p
              className={`text-xs mt-2 ${
                trend.direction === 'up' ? 'text-[#059669]' : 'text-[#DC2626]'
              }`}
            >
              {trend.direction === 'up' ? '↑' : '↓'} {trend.value}
            </p>
          )}
        </div>
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center"
          style={{ backgroundColor: iconBgColor }}
        >
          <Icon className="w-6 h-6" style={{ color: iconColor }} />
        </div>
      </div>
    </div>
  );
}
