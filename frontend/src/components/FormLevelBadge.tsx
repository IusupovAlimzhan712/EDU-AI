interface FormLevelBadgeProps {
  form: 4 | 5;
  className?: string;
}

export function FormLevelBadge({ form, className = '' }: FormLevelBadgeProps) {
  const styles = {
    4: 'bg-[#DBEAFE] text-[#1E3A8A]',
    5: 'bg-[#E0E7FF] text-[#4338CA]',
  };

  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${styles[form]} ${className}`}
    >
      Form {form}
    </span>
  );
}
