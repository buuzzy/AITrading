'use client';

import { AppProgressBar as ProgressBar } from 'next-nprogress-bar';
import { ReactNode } from 'react';

export default function ProgressBarProvider({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <ProgressBar
        height="3px"
        color="#4f46e5" // Indigo-600, a nice modern color. Change to your primary if needed.
        options={{ showSpinner: false }}
        shallowRouting
      />
    </>
  );
}
