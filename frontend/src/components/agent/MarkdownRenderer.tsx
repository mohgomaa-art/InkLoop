import React, { useState } from 'react';
import { Image as ImageIcon, ExternalLink, RefreshCw } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  onImageClick?: (src: string, alt: string) => void;
}

export const resolveImageUrl = (rawSrc: string): string => {
  if (!rawSrc) return '';
  const s = rawSrc.trim();
  if (s.startsWith('http://') || s.startsWith('https://') || s.startsWith('data:') || s.startsWith('blob:')) {
    return s;
  }
  if (s.startsWith('/api/v1/assets/') && s.endsWith('/file')) {
    return s;
  }
  if (s.startsWith('/api/')) {
    return s;
  }
  if (s.startsWith('/static/')) {
    return s;
  }
  if (s.startsWith('runs/m0_visual/reference/')) {
    return `/static/reference/${s.replace('runs/m0_visual/reference/', '')}`;
  }
  if (s.startsWith('art_') || s.startsWith('asset_')) {
    return `/api/v1/assets/${encodeURIComponent(s)}/file`;
  }
  if (s.startsWith('objects/')) {
    const parts = s.split('/');
    const fname = parts[parts.length - 1];
    return `/api/v1/assets/${encodeURIComponent(fname)}/file`;
  }
  if (s.startsWith('/')) {
    return s;
  }
  return `/api/v1/assets/${encodeURIComponent(s)}/file`;
};

const ChatImage: React.FC<{
  src: string;
  alt?: string;
  onClick?: () => void;
  className?: string;
}> = ({ src, alt, onClick, className = '' }) => {
  const [hasError, setHasError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const resolved = resolveImageUrl(src);

  if (hasError) {
    return (
      <div className="my-2 p-3 rounded-xl border border-white/10 bg-ink-950 flex flex-col items-center justify-center gap-2 text-center text-xs text-ink-400 max-w-md">
        <ImageIcon className="w-5 h-5 text-ink-500" />
        <span className="font-mono text-[11px] text-ink-300 truncate max-w-xs">{alt || 'Image preview unavailable'}</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setHasError(false);
              setLoading(true);
              setRetryKey((k) => k + 1);
            }}
            className="px-2.5 py-1 rounded bg-white/10 hover:bg-white/20 text-white text-[10px] flex items-center gap-1 transition-all"
          >
            <RefreshCw className="w-3 h-3" /> Retry load
          </button>
          <a
            href={resolved}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-white text-[10px] flex items-center gap-1 underline underline-offset-2"
          >
            Open asset <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={`my-2.5 rounded-xl overflow-hidden border border-white/10 bg-ink-950 p-2 max-w-md shadow-2xl group cursor-pointer hover:border-white/30 transition-all ${className}`}
    >
      <div className="relative rounded-lg overflow-hidden bg-black/40 flex items-center justify-center min-h-[140px]">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-ink-900/40 text-ink-400 text-xs gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-white" />
            <span className="font-mono text-[10px]">Loading preview...</span>
          </div>
        )}
        <img
          key={retryKey}
          src={resolved}
          alt={alt || 'Generated Artwork'}
          loading="lazy"
          onLoad={() => setLoading(false)}
          onError={() => {
            setLoading(false);
            setHasError(true);
          }}
          className={`w-full h-auto object-contain max-h-[460px] rounded-lg transition-transform duration-300 group-hover:scale-[1.01] ${loading ? 'opacity-0' : 'opacity-100'}`}
        />
      </div>
      <div className="flex items-center justify-between mt-2 px-1 text-[11px] text-ink-400">
        <span className="font-semibold text-white truncate max-w-[220px]">{alt || 'Generated Artwork'}</span>
        <span className="text-ink-400 group-hover:text-white font-mono text-[10px] flex items-center gap-1 group-hover:underline">
          Click to enlarge ↗
        </span>
      </div>
    </div>
  );
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '', onImageClick }) => {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBuffer: string[] = [];
  let codeLang = '';

  const renderInline = (text: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let keyIdx = 0;

    const regex = /(!\[[^\]]*\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`)/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }

      const raw = match[0];
      if (raw.startsWith('![') && raw.includes('](')) {
        const sub = raw.match(/!\[(.*?)\]\((.*?)\)/);
        if (sub) {
          const alt = sub[1];
          const src = sub[2];
          parts.push(
            <ChatImage
              key={keyIdx++}
              src={src}
              alt={alt}
              onClick={() => onImageClick?.(resolveImageUrl(src), alt)}
            />
          );
        }
      } else if (raw.startsWith('**') && raw.endsWith('**')) {
        parts.push(
          <strong key={keyIdx++} className="font-semibold text-white">
            {raw.slice(2, -2)}
          </strong>
        );
      } else if (raw.startsWith('`') && raw.endsWith('`')) {
        parts.push(
          <code
            key={keyIdx++}
            className="px-1.5 py-0.5 rounded bg-ink-800 text-ink-200 border border-white/10 font-mono text-xs"
          >
            {raw.slice(1, -1)}
          </code>
        );
      }
      lastIndex = match.index + raw.length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  lines.forEach((line, lineIdx) => {
    // Code block toggle
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <div key={`code-${lineIdx}`} className="my-3 rounded-xl overflow-hidden border border-white/10 bg-ink-950">
            {codeLang && (
              <div className="px-3 py-1 bg-ink-900 border-b border-white/5 text-[10px] font-mono uppercase text-ink-400">
                {codeLang}
              </div>
            )}
            <pre className="p-3 font-mono text-xs text-ink-200 overflow-x-auto">
              {codeBuffer.join('\n')}
            </pre>
          </div>
        );
        codeBuffer = [];
        codeLang = '';
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeLang = line.trim().slice(3).trim();
      }
      return;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      return;
    }

    // Headings
    if (line.startsWith('### ')) {
      elements.push(
        <h4 key={`h3-${lineIdx}`} className="text-sm font-bold text-white mt-3 mb-1 flex items-center gap-2">
          {renderInline(line.slice(4))}
        </h4>
      );
      return;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h3 key={`h2-${lineIdx}`} className="text-base font-bold text-white mt-4 mb-1.5 flex items-center gap-2">
          {renderInline(line.slice(3))}
        </h3>
      );
      return;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <h2 key={`h1-${lineIdx}`} className="text-lg font-bold text-white mt-4 mb-2">
          {renderInline(line.slice(2))}
        </h2>
      );
      return;
    }

    // Blockquote
    if (line.startsWith('> ')) {
      elements.push(
        <blockquote
          key={`quote-${lineIdx}`}
          className="border-l-2 border-white/20 pl-3 my-2 text-xs italic text-ink-300 bg-white/[0.02] py-1 rounded-r"
        >
          {renderInline(line.slice(2))}
        </blockquote>
      );
      return;
    }

    // Bullet points
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const bulletText = line.trim().slice(2);
      elements.push(
        <div key={`bullet-${lineIdx}`} className="flex items-start gap-2 my-1 text-xs text-ink-200 leading-relaxed pl-1">
          <span className="w-1.5 h-1.5 rounded-full bg-white shrink-0 mt-1.5" />
          <span>{renderInline(bulletText)}</span>
        </div>
      );
      return;
    }

    // Numbered lists
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      elements.push(
        <div key={`num-${lineIdx}`} className="flex items-start gap-2 my-1 text-xs text-ink-200 leading-relaxed pl-1">
          <span className="text-[11px] font-mono text-ink-300 font-semibold shrink-0 min-w-[16px]">
            {numMatch[1]}.
          </span>
          <span>{renderInline(numMatch[2])}</span>
        </div>
      );
      return;
    }

    // Block image line: ![alt](url)
    const blockImgMatch = line.trim().match(/^!\[(.*?)\]\((.*?)\)$/);
    if (blockImgMatch) {
      const alt = blockImgMatch[1];
      const src = blockImgMatch[2];
      elements.push(
        <ChatImage
          key={`bimg-${lineIdx}`}
          src={src}
          alt={alt}
          onClick={() => onImageClick?.(resolveImageUrl(src), alt)}
        />
      );
      return;
    }

    // Empty line / paragraph break
    if (!line.trim()) {
      elements.push(<div key={`empty-${lineIdx}`} className="h-2" />);
      return;
    }

    // Standard paragraph line
    elements.push(
      <p key={`p-${lineIdx}`} className="my-1 text-xs text-ink-200 leading-relaxed">
        {renderInline(line)}
      </p>
    );
  });

  return <div className={`markdown-content space-y-0.5 ${className}`}>{elements}</div>;
};
