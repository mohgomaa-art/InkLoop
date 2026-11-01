import React from 'react';

interface LogoProps {
  className?: string;
  size?: number;
}

/**
 * Meta AI Infinity Symbol (Used for Meta Muse Spark & Meta AI Ecosystem)
 */
export const MetaLogo: React.FC<LogoProps> = ({ className = 'w-4 h-4', size }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    style={size ? { width: size, height: size } : undefined}
    aria-hidden="true"
  >
    <path d="M16.96 4C14.74 4 13.06 5.16 12 6.57C10.94 5.16 9.26 4 7.04 4C3.15 4 0 7.15 0 11.04C0 14.93 3.15 18.08 7.04 18.08C9.26 18.08 10.94 16.92 12 15.51C13.06 16.92 14.74 18.08 16.96 18.08C20.85 18.08 24 14.93 24 11.04C24 7.15 20.85 4 16.96 4ZM7.04 15.76C4.43 15.76 2.32 13.65 2.32 11.04C2.32 8.43 4.43 6.32 7.04 6.32C8.82 6.32 10.38 7.37 11.23 8.95C10.63 10.23 9.8 11.45 8.78 12.55C8.28 13.09 7.7 13.56 7.04 13.91V15.76ZM16.96 15.76C15.18 15.76 13.62 14.71 12.77 13.13C13.37 11.85 14.2 10.63 15.22 9.53C15.72 8.99 16.3 8.52 16.96 8.17V6.32C19.57 6.32 21.68 8.43 21.68 11.04C21.68 13.65 19.57 15.76 16.96 15.76Z" />
  </svg>
);

/**
 * Anthropic Claude Sunburst Spark
 */
export const ClaudeLogo: React.FC<LogoProps> = ({ className = 'w-4 h-4', size }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    style={size ? { width: size, height: size } : undefined}
    aria-hidden="true"
  >
    <path d="M12 2L13.82 8.18L20 10L13.82 11.82L12 18L10.18 11.82L4 10L10.18 8.18L12 2Z" />
    <path d="M18.5 2.5L19.5 5.5L22.5 6.5L19.5 7.5L18.5 10.5L17.5 7.5L14.5 6.5L17.5 5.5L18.5 2.5Z" opacity="0.85" />
    <path d="M5.5 15.5L6.3 17.7L8.5 18.5L6.3 19.3L5.5 21.5L4.7 19.3L2.5 18.5L4.7 17.7L5.5 15.5Z" opacity="0.7" />
  </svg>
);

/**
 * Google Gemini Multimodal Star (Exact cubic-bezier geometry with brand gradient)
 */
export const GeminiLogo: React.FC<LogoProps> = ({ className = 'w-4 h-4', size }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    className={className}
    style={size ? { width: size, height: size } : undefined}
    aria-hidden="true"
  >
    <path
      d="M12 24C12 17.373 6.627 12 0 12C6.627 12 12 6.627 12 0C12 6.627 17.373 12 24 12C17.373 12 12 17.373 12 24Z"
      fill="url(#gemini-sparkle-gradient)"
    />
    <defs>
      <linearGradient id="gemini-sparkle-gradient" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">
        <stop stopColor="#1BA1E3" />
        <stop offset="0.5" stopColor="#6C5CE7" />
        <stop offset="1" stopColor="#E056FD" />
      </linearGradient>
    </defs>
  </svg>
);

/**
 * OpenAI Rosette / Spiral Vortex
 */
export const OpenAILogo: React.FC<LogoProps> = ({ className = 'w-4 h-4', size }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    style={size ? { width: size, height: size } : undefined}
    aria-hidden="true"
  >
    <path d="M22.28 9.68a5.57 5.57 0 0 0-.49-4.7 5.68 5.68 0 0 0-4.04-2.6 5.6 5.6 0 0 0-4.87 1.15 5.68 5.68 0 0 0-7.3 2.14 5.6 5.6 0 0 0-.85 4.95 5.68 5.68 0 0 0-3.23 3.6 5.6 5.6 0 0 0 .5 5 5.68 5.68 0 0 0 4.04 2.6 5.6 5.6 0 0 0 4.87-1.15 5.68 5.68 0 0 0 7.3-2.14 5.6 5.6 0 0 0 .85-4.95 5.68 5.68 0 0 0 3.22-3.6zM13.2 21.6a3.9 3.9 0 0 1-2.48-.88l.12-.07 4.12-2.38a.9.9 0 0 0 .45-.78v-5.83l1.75 1.01a.1.1 0 0 1 .05.08v4.96a3.92 3.92 0 0 1-4.01 3.89zm-8.8-3.9a3.9 3.9 0 0 1-.49-2.6l.12.07 4.12 2.38a.9.9 0 0 0 .9 0l5.05-2.92v2.02a.1.1 0 0 1-.04.09l-4.3 2.48a3.92 3.92 0 0 1-5.36-1.52zm-1.85-8.87a3.9 3.9 0 0 1 2-1.72v4.89a.9.9 0 0 0 .45.78l5.05 2.92-1.75 1.01a.1.1 0 0 1-.1 0l-4.3-2.48a3.92 3.92 0 0 1-1.35-5.4zm10.74-2.66l-4.12 2.38a.9.9 0 0 0-.45.78v5.83L7.07 14.2a.1.1 0 0 1-.05-.08V9.16a3.92 3.92 0 0 1 5.96-3.35l.31.18zm4.84 5.8a.9.9 0 0 0-.9 0l-5.05 2.92V12.9a.1.1 0 0 1 .04-.09l4.3-2.48a3.92 3.92 0 0 1 5.36 1.52 3.9 3.9 0 0 1 .49 2.6l-.12-.07-4.12-2.38zm1.85 3.07a3.9 3.9 0 0 1-2 1.72V11.94a.9.9 0 0 0-.45-.78L12.53 8.24l1.75-1.01a.1.1 0 0 1 .1 0l4.3 2.48a3.92 3.92 0 0 1 1.35 5.4z" />
  </svg>
);

/**
 * DeepSeek Reasoning Emblem
 */
export const DeepSeekLogo: React.FC<LogoProps> = ({ className = 'w-4 h-4', size }) => (
  <svg
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
    style={size ? { width: size, height: size } : undefined}
    aria-hidden="true"
  >
    <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" opacity="0.4" />
    <path d="M15.5 8.5C14.1 7.1 11.9 7.1 10.5 8.5L7.5 11.5C6.1 12.9 6.1 15.1 7.5 16.5C8.9 17.9 11.1 17.9 12.5 16.5L15.5 13.5C16.9 12.1 16.9 9.9 15.5 8.5ZM11.5 15C10.7 15.8 9.3 15.8 8.5 15C7.7 14.2 7.7 12.8 8.5 12L11.5 9C12.3 8.2 13.7 8.2 14.5 9C15.3 9.8 15.3 11.2 14.5 12L11.5 15Z" />
  </svg>
);

/**
 * Meta Muse Image Generation Engine Emblem
 */
export const MuseImageLogo: React.FC<LogoProps> = ({ className = 'w-4 h-4', size }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    className={className}
    style={size ? { width: size, height: size } : undefined}
    aria-hidden="true"
  >
    <rect x="3" y="3" width="18" height="18" rx="5" stroke="currentColor" strokeWidth="1.8" />
    <circle cx="8.5" cy="8.5" r="2" fill="currentColor" />
    <path d="M21 15L15.5 9.5L6 19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
