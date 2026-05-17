import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
  className?: string;
}

/**
 * Renders AI tutor responses as formatted markdown.
 * Scoped styles keep the design consistent with the app palette.
 */
export function MarkdownMessage({ content, className = '' }: Props) {
  return (
    <div className={`prose-eduai text-sm leading-relaxed ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-[#111827] mt-3 mb-1 first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-[#111827] mt-3 mb-1 first:mt-0">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-[#1E3A8A] mt-2.5 mb-1 first:mt-0">{children}</h3>
          ),

          // Paragraphs
          p: ({ children }) => (
            <p className="mb-2 last:mb-0 whitespace-pre-wrap break-words">{children}</p>
          ),

          // Bold / italic
          strong: ({ children }) => (
            <strong className="font-semibold text-[#111827]">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-[#374151]">{children}</em>
          ),

          // Unordered list
          ul: ({ children }) => (
            <ul className="mt-1 mb-2 space-y-1 pl-4 last:mb-0">{children}</ul>
          ),
          // Ordered list
          ol: ({ children }) => (
            <ol className="mt-1 mb-2 space-y-1 pl-4 list-decimal last:mb-0">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="flex gap-2 break-words">
              <span className="flex-shrink-0 mt-1.5 w-1.5 h-1.5 rounded-full bg-[#1E3A8A] inline-block" />
              <span className="flex-1 min-w-0">{children}</span>
            </li>
          ),

          // Inline code
          code: ({ children }) => (
            <code className="px-1 py-0.5 rounded bg-[#F3F4F6] text-[#1E3A8A] text-xs font-mono">
              {children}
            </code>
          ),

          // Horizontal rule
          hr: () => <hr className="my-2 border-[#E5E7EB]" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
