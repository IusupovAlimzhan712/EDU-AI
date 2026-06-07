import { useEffect, useId, useRef, useState } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSize: '14px',
  },
  flowchart: {
    curve: 'basis',
    padding: 20,
  },
  securityLevel: 'loose',
});

interface MermaidDiagramProps {
  source: string;
  className?: string;
}

export function MermaidDiagram({ source, className = '' }: MermaidDiagramProps) {
  const uid = useId().replace(/:/g, '');
  const id = `mermaid-${uid}`;
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    setError(null);
    mermaid.render(id, source)
      .then(({ svg }) => {
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
          // Make SVG responsive
          const svgEl = containerRef.current.querySelector('svg');
          if (svgEl) {
            svgEl.style.maxWidth = '100%';
            svgEl.style.height = 'auto';
          }
        }
      })
      .catch((err) => {
        setError(`Diagram could not be rendered: ${err?.message ?? 'unknown error'}`);
      });
  }, [id, source]);

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-[#FEE2E2] border border-[#DC2626]/20 text-sm text-[#991B1B]">
        {error}
      </div>
    );
  }

  return <div ref={containerRef} className={`overflow-x-auto ${className}`} />;
}
