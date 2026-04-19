interface CircularProgressProps {
  percentage: number;
  size?: 'small' | 'medium' | 'large';
  color?: string;
  className?: string;
}

export function CircularProgress({
  percentage,
  size = 'medium',
  color = '#059669',
  className = '',
}: CircularProgressProps) {
  const sizes = {
    small: { diameter: 48, strokeWidth: 6, fontSize: 'text-xs' },
    medium: { diameter: 80, strokeWidth: 6, fontSize: 'text-lg' },
    large: { diameter: 120, strokeWidth: 8, fontSize: 'text-2xl' },
  };

  const { diameter, strokeWidth, fontSize } = sizes[size];
  const radius = (diameter - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`relative inline-flex ${className}`} style={{ width: diameter, height: diameter }}>
      <svg width={diameter} height={diameter} className="transform -rotate-90">
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          stroke="#E5E7EB"
          strokeWidth={strokeWidth}
          fill="none"
        />
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500"
        />
      </svg>
      <div className={`absolute inset-0 flex items-center justify-center ${fontSize} font-semibold`}>
        {percentage}%
      </div>
    </div>
  );
}
