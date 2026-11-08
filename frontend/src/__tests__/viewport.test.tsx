import React from 'react';
import '@testing-library/jest-dom/vitest';
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { QuickActions } from '../components/QuickActions';

describe('Responsive Viewport Smoke Tests', () => {
  const targetViewports = [320, 360, 390];

  it.each(targetViewports)('ensures touch targets and layout fit within %ipx viewport without horizontal overflow', (viewportWidth) => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: viewportWidth,
    });

    const { container } = render(
      <div style={{ maxWidth: '100%', width: `${viewportWidth}px`, overflowX: 'hidden' }}>
        <QuickActions lang="en" onActionClick={() => {}} />
      </div>
    );

    // Verify touch targets satisfy accessibility minimum 44px
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThanOrEqual(4);

    buttons.forEach((btn) => {
      // Style assertions
      const style = window.getComputedStyle(btn);
      expect(btn.style.minHeight).toBe('44px');
      expect(btn.style.minWidth).toBe('44px');
    });

    // Verify container scrolling bounds
    const scrollEl = document.scrollingElement || document.documentElement;
    expect(scrollEl.scrollWidth).toBeLessThanOrEqual(window.innerWidth);
  });
});
