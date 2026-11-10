import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api/client';

describe('API client URL resolution', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('resolves API paths against the current origin before calling fetch', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal('fetch', fetchMock);

    await api.listActiveNotices('en');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe(`${window.location.origin}/api/v1/notices?lang=en`);
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ credentials: 'include' }));
  });
});
