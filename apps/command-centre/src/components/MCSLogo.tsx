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
          <div className="absolute -inset-1 bg-gradient-to-r from-orange-500 to-amber-500 rounded-xl blur-xs opacity-60 group-hover:opacity-100 transition duration-300"></div>
          <img
            src="/mcs_logo_3d.jpg"
            alt="Multimedia Cloud Solutions"
            width={img}
            height={img}
            className="relative rounded-lg object-cover shadow-lg border border-orange-400/30"
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
            className="drop-shadow-[0_0_12px_rgba(249,115,22,0.45)]"
          >
            <defs>
              <linearGradient id="logo-m-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#FDBA74" />
                <stop offset="0.5" stopColor="#F97316" />
                <stop offset="1" stopColor="#C2410C" />
              </linearGradient>
              <linearGradient id="logo-core-grad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#FFF7ED" />
                <stop offset="1" stopColor="#FBBF24" />
              </linearGradient>
            </defs>

            {/* Badge */}
            <rect width="48" height="48" rx="12" fill="#0C0A09" />
            <rect x="0.75" y="0.75" width="46.5" height="46.5" rx="11.25" stroke="#F97316" strokeOpacity="0.35" strokeWidth="1.5" />

            {/* Broadcast signal arcs */}
            <path d="M 14 12.5 Q 24 4.5 34 12.5" stroke="#FDBA74" strokeOpacity="0.35" strokeWidth="1.6" strokeLinecap="round" />
            <path d="M 18 14 Q 24 9 30 14" stroke="#FB923C" strokeOpacity="0.8" strokeWidth="1.6" strokeLinecap="round" />

            {/* M monogram */}
            <polygon points="10,40 10,19 16.5,19 24,29.5 31.5,19 38,19 38,40 32,40 32,28.5 24,39 16,28.5 16,40" fill="url(#logo-m-grad)" />
            <polygon points="24,29.5 31.5,19 38,19 38,40 32,40 32,28.5 24,39" fill="#FFFFFF" fillOpacity="0.12" />

            {/* Core node */}
            <polygon points="24,19 27.5,22.5 24,26 20.5,22.5" fill="url(#logo-core-grad)" />
          </svg>
        </div>
      )}

      {/* Wordmark Typography */}
      {variant !== 'mark' && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5 leading-none">
            <span className={`font-extrabold tracking-tight text-orange-50 font-mono ${text}`}>
              MCS
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse"></span>
            {variant === 'full' && (
              <span className="text-[11px] font-bold tracking-widest uppercase text-orange-400 ml-0.5">
                MEDIA CLOUD
              </span>
            )}
          </div>
          {variant === 'full' && (
            <span className={`font-semibold uppercase tracking-[0.2em] text-stone-400 mt-1 leading-none ${sub}`}>
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
