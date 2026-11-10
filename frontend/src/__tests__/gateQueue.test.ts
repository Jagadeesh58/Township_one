import 'fake-indexeddb/auto';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  acknowledgeGateQueueEntry,
  clearGateQueueForTests,
  expireOldGatePhotos,
  getGateQueueEntry,
  getGateQueueSummary,
  getGateDeviceIdentity,
  listGateQueueEntries,
  queueVisitorPhoto,
  recordGateSyncFailure,
  sha256Blob,
  type SignedTimeAnchor,
} from '../lib/gateQueue';

const day = 24 * 60 * 60 * 1000;
const baseNow = Date.parse('2026-11-09T12:00:00.000Z');

async function queueOne(now = baseNow) {
  const identity = await getGateDeviceIdentity();
  const timeAnchor: SignedTimeAnchor = {
    payload: {
      user_id: 'guard-user-001',
      gate_id: 'gate_1',
      device_id: identity.deviceId,
      device_generation_id: identity.generationId,
      server_time_utc: new Date(now).toISOString(),
      timestamp_unix: Math.floor(now / 1000),
      valid_until_unix: Math.floor(now / 1000) + 86400,
    },
    signature: 'signed-test-anchor',
    algorithm: 'ECDSA_P256_SHA256',
    device_time_at_receipt: now,
  };
  const photo = new Blob(['visitor-photo-bytes'], { type: 'image/jpeg' });
  return queueVisitorPhoto({
    userId: 'guard-user-001',
    gateId: 'gate_1',
    flatId: 'flat-1203',
    visitorName: 'Sample Visitor',
    purpose: 'Delivery',
    photo,
    timeAnchor,
    now,
  });
}

describe('durable gate visitor queue', () => {
  beforeEach(async () => {
    await clearGateQueueForTests();
    vi.stubGlobal('navigator', {
      ...navigator,
      storage: {
        persist: vi.fn().mockResolvedValue(true),
        estimate: vi.fn().mockResolvedValue({ quota: 100 * 1024 * 1024, usage: 1024 }),
      },
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it('persists the actual photo Blob and verifies its hash after reading it back', async () => {
    const queued = await queueOne();
    const stored = await getGateQueueEntry(queued.eventUuid);
    expect(stored?.photoBlob).toBeInstanceOf(Blob);
    expect(await sha256Blob(stored!.photoBlob!)).toBe(queued.sha256);
    expect(stored?.status).toBe('PENDING');
  });

  it('uses FileReader when the Blob implementation has no arrayBuffer method', async () => {
    const photo = new Blob(['legacy-jsdom-photo'], { type: 'image/jpeg' });
    Object.defineProperty(photo, 'arrayBuffer', { configurable: true, value: undefined });
    const expectedHash = await sha256Blob(new Blob(['legacy-jsdom-photo'], { type: 'image/jpeg' }));
    expect(await sha256Blob(photo)).toBe(expectedHash);
  });

  it('retains photo bytes after a failed synchronization and schedules backoff', async () => {
    const queued = await queueOne();
    await recordGateSyncFailure(queued.eventUuid, 'HTTP 503', baseNow);
    const stored = await getGateQueueEntry(queued.eventUuid);
    expect(stored?.photoBlob).toBeInstanceOf(Blob);
    expect(stored?.status).toBe('RETRY');
    expect(stored?.lastError).toBe('HTTP 503');
    expect(stored!.nextRetryAt).toBeGreaterThan(baseNow);
  });

  it('removes photo bytes only after explicit server acknowledgement', async () => {
    const queued = await queueOne();
    expect((await getGateQueueEntry(queued.eventUuid))?.photoBlob).toBeInstanceOf(Blob);
    await acknowledgeGateQueueEntry(queued.eventUuid);
    const stored = await getGateQueueEntry(queued.eventUuid);
    expect(stored?.photoBlob).toBeNull();
    expect(stored?.status).toBe('ACKNOWLEDGED');
    expect(stored?.visitorName).toBe('');
    expect(stored?.flatId).toBe('');
    expect(stored?.purpose).toBe('');
    expect(stored?.phone).toBeUndefined();
    expect(stored?.preApprovalCredential).toBeUndefined();
  });

  it('expires unsynchronized photo bytes after 90 days and keeps only metadata', async () => {
    const queued = await queueOne();
    const expired = await expireOldGatePhotos(new Date(queued.captureTime).getTime() + 91 * day);
    const stored = await getGateQueueEntry(queued.eventUuid);
    expect(expired).toBe(1);
    expect(stored?.photoBlob).toBeNull();
    expect(stored?.status).toBe('EXPIRED');
    expect(stored?.visitorName).toBe('');
    expect(stored?.flatId).toBe('');
    expect(stored?.purpose).toBe('');
  });

  it('reports pending count and oldest queue age', async () => {
    const queued = await queueOne();
    const summary = await getGateQueueSummary(new Date(queued.captureTime).getTime() + 60_000);
    expect(summary.pendingCount).toBe(1);
    expect(summary.oldestAgeMs).toBe(60_000);
  });

  it('does not leave a queue row when the IndexedDB write transaction fails', async () => {
    const addSpy = vi.spyOn(IDBObjectStore.prototype, 'add').mockImplementation(() => {
      throw new DOMException('Storage write failed', 'QuotaExceededError');
    });
    await expect(queueOne()).rejects.toThrow();
    addSpy.mockRestore();
    expect(await listGateQueueEntries()).toHaveLength(0);
  });

  it('blocks saving when persistent storage reports insufficient space', async () => {
    vi.stubGlobal('navigator', {
      ...navigator,
      storage: {
        persist: vi.fn().mockResolvedValue(false),
        estimate: vi.fn().mockResolvedValue({ quota: 5 * 1024 * 1024, usage: 4 * 1024 * 1024 }),
      },
    });
    await expect(queueOne()).rejects.toThrow(/storage is unavailable|low on space/i);
    expect(await listGateQueueEntries()).toHaveLength(0);
  });


  it('uses IndexedDB when StorageManager persistence APIs are unsupported', async () => {
    vi.stubGlobal('navigator', { ...navigator, storage: undefined });
    const queued = await queueOne();
    const stored = await getGateQueueEntry(queued.eventUuid);
    expect(stored?.photoBlob).toBeInstanceOf(Blob);
    expect(stored?.sha256).toBe(queued.sha256);
  });

  it('refuses to queue an anchor issued for another guard or gate', async () => {
    const queued = await queueOne();
    const anchor = queued.timeAnchor;
    await expect(queueVisitorPhoto({
      userId: 'different-guard',
      gateId: 'gate_1',
      flatId: 'flat-1203',
      visitorName: 'Sample Visitor',
      purpose: 'Delivery',
      photo: new Blob(['photo'], { type: 'image/jpeg' }),
      timeAnchor: anchor,
    })).rejects.toThrow(/time anchor/i);
  });
});
