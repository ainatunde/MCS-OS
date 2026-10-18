'use client';

import React from 'react';
import Link from 'next/link';

interface MCSLogoProps {
  variant?: 'full' | 'mark' | '3d' | 'compact';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  showLink?: boolean;
}

export default function MCSLogo({
  variant = 'full',
  size = 'md',
  className = '',
  showLink = true,
}: MCSLogoProps) {
  const sizeMap = {
    sm: { img: 28, text: 'text-base', sub: 'text-[7.5px]', emblem: 28 },
    md: { img: 38, text: 'text-xl', sub: 'text-[9px]', emblem: 38 },
    lg: { img: 52, text: 'text-2xl', sub: 'text-[10px]', emblem: 52 },
    xl: { img: 72, text: 'text-4xl', sub: 'text-xs', emblem: 72 },
  };

  const { img, text, sub, emblem } = sizeMap[size];

  const content = (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* 3D or Vector Emblem */}
      {variant === '3d' ? (
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-indigo-600 rounded-xl blur-xs opacity-60 group-hover:opacity-100 transition duration-300"></div>
          <img
            src="/mcs_logo_3d.jpg"
            alt="Multimedia Cloud Solutions"
            width={img}
            height={img}
            className="relative rounded-lg object-cover shadow-lg border border-cyan-400/30"
          />
        </div>
      ) : (
        <div className="relative flex items-center justify-center">
          <svg
            width={emblem}
            height={emblem}
            viewBox="0 0 48 48"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="drop-shadow-[0_0_12px_rgba(0,229,255,0.4)]"
          >
            <defs>
              <linearGradient id="logo-left-grad" x1="0%" y1="100%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#0284C7" />
                <stop offset="100%" stopColor="#00E5FF" />
              </linearGradient>
              <linearGradient id="logo-right-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#7C4DFF" />
                <stop offset="50%" stopColor="#6366F1" />
                <stop offset="100%" stopColor="#00E5FF" />
              </linearGradient>
              <linearGradient id="logo-core-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#00E5FF" />
                <stop offset="100%" stopColor="#10B981" />
              </linearGradient>
            </defs>

            {/* Background Badge */}
            <rect width="48" height="48" rx="12" fill="#0A0F1D" stroke="#1E293B" strokeWidth="1.5" />
            <rect width="46" height="46" x="1" y="1" rx="11" fill="none" stroke="rgba(0, 229, 255, 0.25)" strokeWidth="1" />

            {/* Broadcast Waves */}
            <path d="M 12 14 C 18 9, 30 9, 36 14" stroke="#00E5FF" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
            <path d="M 16 17 C 20 13, 28 13, 32 17" stroke="#7C4DFF" strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />

            {/* M-Wings */}
            <path d="M 11 36 L 11 20 C 11 17 14 15.5 17 17.5 L 24 23 L 20.5 27 L 16.5 23.5 L 16.5 36 Z" fill="url(#logo-left-grad)" />
            <path d="M 37 36 L 37 20 C 37 17 34 15.5 31 17.5 L 24 23 L 27.5 27 L 31.5 23.5 L 31.5 36 Z" fill="url(#logo-right-grad)" />

            {/* Diamond Core */}
            <polygon points="24,24.5 28.5,29 24,33.5 19.5,29" fill="url(#logo-core-grad)" />
            <circle cx="24" cy="29" r="1.5" fill="#FFFFFF" />
          </svg>
        </div>
      )}

      {/* Wordmark Typography */}
      {variant !== 'mark' && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5 leading-none">
            <span className={`font-extrabold tracking-tight text-white font-mono ${text}`}>
              MCS
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
            {variant === 'full' && (
              <span className="text-[11px] font-bold tracking-widest uppercase text-cyan-400/90 ml-0.5">
                MEDIA CLOUD
              </span>
            )}
          </div>
          {variant === 'full' && (
            <span className={`font-semibold uppercase tracking-[0.2em] text-slate-400 mt-1 leading-none ${sub}`}>
              Multimedia Cloud Solutions
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (showLink) {
    return (
      <Link href="/products" className="hover:opacity-95 transition">
        {content}
      </Link>
    );
  }

  return content;
}
