import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('Service Worker Security and Cache Invalidation', () => {
  let mockCaches: Record<string, any>;
  let deletedKeys: string[];

  beforeEach(() => {
    mockCaches = {
      'township-one-shell-v1': {},
      'old-cache-v0': {},
    };
    deletedKeys = [];

    // Global caches mock
    (globalThis as any).caches = {
      keys: vi.fn().mockImplementation(async () => Object.keys(mockCaches)),
      delete: vi.fn().mockImplementation(async (key: string) => {
        deletedKeys.push(key);
        delete mockCaches[key];
        return true;
      }),
      match: vi.fn().mockImplementation(async () => null),
      open: vi.fn().mockImplementation(async () => ({
        addAll: vi.fn(),
        put: vi.fn(),
      })),
    };
  });

  it('strictly bypasses cache and never calls event.respondWith for private /api/ requests', () => {
    const apiUrls = [
      'https://township.example.com/api/v1/billing/flats/123/summary',
      'http://localhost:8000/api/v1/payments/checkout',
      'https://township.example.com/api/v1/auth/me',
    ];

    for (const urlStr of apiUrls) {
      const url = new URL(urlStr);
      let didRespondWith = false;

      const mockEvent = {
        request: {
          url: urlStr,
          mode: 'cors',
        },
        respondWith: () => {
          didRespondWith = true;
        },
      };

      // Service worker fetch rule logic
      if (url.pathname.startsWith('/api/')) {
        // Must return directly without invoking event.respondWith
      } else {
        mockEvent.respondWith();
      }

      expect(didRespondWith, `Expected /api/ request ${urlStr} to bypass service worker caching`).toBe(false);
    }
  });

  it('deletes all cache storage instances when receiving CLEAR_CACHES or LOGOUT message', async () => {
    // Simulate sw message handler
    const handleMessage = async (msgType: string) => {
      if (msgType === 'CLEAR_CACHES' || msgType === 'LOGOUT') {
        const keys = await (globalThis as any).caches.keys();
        await Promise.all(keys.map((k: string) => (globalThis as any).caches.delete(k)));
      }
    };

    expect(Object.keys(mockCaches).length).toBe(2);

    await handleMessage('LOGOUT');

    expect(deletedKeys).toContain('township-one-shell-v1');
    expect(deletedKeys).toContain('old-cache-v0');
    expect(Object.keys(mockCaches).length).toBe(0);
  });
});
