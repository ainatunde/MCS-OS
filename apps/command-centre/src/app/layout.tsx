import React from 'react';

export const metadata = {
  title: 'MCS-OS Executive Command Centre',
  description: 'Multimedia Cloud Solutions Autonomous Operating System v2.2',
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
