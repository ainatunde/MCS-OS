import React from 'react';
import './globals.css';

export const metadata = {
  title: 'Multimedia Cloud Solutions | MCS-OS',
  description: 'Autonomous Media Infrastructure, Broadcast Playout, Dynamic Ad Insertion & Enterprise Operating System',
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
    apple: '/favicon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
