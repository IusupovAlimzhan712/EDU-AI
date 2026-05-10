interface StatusBadgeProps {
  status: 'completed' | 'in-progress' | 'not-started' | 'locked';
  className?: string;
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const styles = {
    completed: 'bg-[#D1FAE5] text-[#059669]',
    'in-progress': 'bg-[#DBEAFE] text-[#1E3A8A]',
    'not-started': 'bg-[#F3F4F6] text-[#6B7280]',
    locked: 'bg-[#FEE2E2] text-[#DC2626]',
  };

  const labels = {
    completed: 'Completed',
    'in-progress': 'In Progress',
    'not-started': 'Not Started',
    locked: 'Locked',
  };

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${styles[status]} ${className}`}
    >
      {labels[status]}
    </span>
  );
}
