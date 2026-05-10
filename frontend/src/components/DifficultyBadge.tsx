interface DifficultyBadgeProps {
  difficulty: 'easy' | 'medium' | 'hard';
  className?: string;
}

export function DifficultyBadge({ difficulty, className = '' }: DifficultyBadgeProps) {
  const styles = {
    easy: 'bg-[#D1FAE5] text-[#059669]',
    medium: 'bg-[#FEF3C7] text-[#D97706]',
    hard: 'bg-[#FEE2E2] text-[#DC2626]',
  };

  const labels = {
    easy: 'Easy',
    medium: 'Medium',
    hard: 'Hard',
  };

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${styles[difficulty]} ${className}`}
    >
      {labels[difficulty]}
    </span>
  );
}
