export interface SignedTimeAnchor {
  payload: {
    user_id: string;
    gate_id: string;
    device_id: string;
    device_generation_id: string;
    server_time_utc: string;
    timestamp_unix: number;
    valid_until_unix: number;
  };
  signature: string;
  algorithm: 'ECDSA_P256_SHA256';
  device_time_at_receipt: number;
}

export interface GateQueueEntry {
  eventUuid: string;
  photoUuid: string;
  gateId: string;
  deviceId: string;
  deviceGenerationId: string;
  deviceSequence: number;
  captureTime: string;
  visitorName: string;
  flatId: string;
  purpose: string;
  phone?: string;
  preApprovalCredential?: string;
  photoBlob: Blob | null;
  mimeType: string;
  size: number;
  sha256: string;
  timeAnchor: SignedTimeAnchor;
  status: 'PENDING' | 'RETRY' | 'ACKNOWLEDGED' | 'EXPIRED';
  retryCount: number;
  nextRetryAt: number;
  lastError?: string;
  createdAt: number;
}

interface DeviceRecord {
  id: 'device';
  deviceId: string;
  generationId: string;
  sequence: number;
}

interface StoredAnchor {
  id: string;
  anchor: SignedTimeAnchor;
}

const DB_NAME = 'township-one-gate-queue';
const DB_VERSION = 1;
const QUEUE_STORE = 'queue';
const META_STORE = 'meta';
const PHOTO_MAX_AGE_MS = 90 * 24 * 60 * 60 * 1000;

function requireIndexedDb(): IDBFactory {
  if (typeof indexedDB === 'undefined') {
    throw new Error('This browser does not provide IndexedDB. Visitor photo cannot be saved offline.');
  }
  return indexedDB;
}

function randomId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  throw new Error('Secure UUID generation is unavailable on this device.');
}

function transactionDone(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onabort = () => reject(tx.error ?? new Error('IndexedDB transaction aborted.'));
    tx.onerror = () => reject(tx.error ?? new Error('IndexedDB transaction failed.'));
  });
}

function requestValue<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('IndexedDB request failed.'));
  });
}

let databasePromise: Promise<IDBDatabase> | undefined;

export function openGateQueueDb(): Promise<IDBDatabase> {
  if (databasePromise) return databasePromise;
  const factory = requireIndexedDb();
  databasePromise = new Promise((resolve, reject) => {
    const request = factory.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(QUEUE_STORE)) db.createObjectStore(QUEUE_STORE, { keyPath: 'eventUuid' });
      if (!db.objectStoreNames.contains(META_STORE)) db.createObjectStore(META_STORE, { keyPath: 'id' });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => {
      databasePromise = undefined;
      reject(request.error ?? new Error('Unable to open durable gate storage.'));
    };
    request.onblocked = () => reject(new Error('Gate storage is blocked by another application tab.'));
  });
  return databasePromise;
}

export async function requestPersistentGateStorage(): Promise<{ persisted: boolean; lowSpace: boolean }> {
  if (typeof navigator === 'undefined' || !navigator.storage) {
    // StorageManager is not implemented in every browser; IndexedDB read-back
    // and hash verification still provide a safe capability check in that case.
    return { persisted: false, lowSpace: false };
  }
  const storageManager = navigator.storage as unknown as {
    persist?: () => Promise<boolean>;
    estimate?: () => Promise<StorageEstimate>;
  };
  const persistMethod = storageManager.persist;
  const estimateMethod = storageManager.estimate;
  const persistSupported = typeof persistMethod === 'function';
  const estimateSupported = typeof estimateMethod === 'function';

  let persisted = false;
  if (persistSupported) {
    try { persisted = await persistMethod.call(storageManager); } catch { persisted = false; }
  }
  let lowSpace = persistSupported && !persisted;
  if (estimateSupported) {
    try {
      const estimate = await estimateMethod.call(storageManager);
      const quota = estimate.quota ?? 0;
      const usage = estimate.usage ?? 0;
      lowSpace = lowSpace || quota <= 0 || quota - usage < 10 * 1024 * 1024;
    } catch { lowSpace = true; }
  }
  return { persisted, lowSpace };
}

export async function saveSignedTimeAnchor(userId: string, gateId: string, anchor: Omit<SignedTimeAnchor, 'device_time_at_receipt'>): Promise<void> {
  const db = await openGateQueueDb();
  const tx = db.transaction(META_STORE, 'readwrite');
  const record: StoredAnchor = {
    id: `anchor:${userId}:${gateId}`,
    anchor: { ...anchor, device_time_at_receipt: Date.now() },
  };
  tx.objectStore(META_STORE).put(record);
  await transactionDone(tx);
}

export async function getSignedTimeAnchor(userId: string, gateId: string): Promise<SignedTimeAnchor | null> {
  const db = await openGateQueueDb();
  const tx = db.transaction(META_STORE, 'readonly');
  const record = await requestValue(tx.objectStore(META_STORE).get(`anchor:${userId}:${gateId}`)) as StoredAnchor | undefined;
  await transactionDone(tx);
  return record?.anchor ?? null;
}

export async function getGateDeviceIdentity(): Promise<{ deviceId: string; generationId: string; sequence: number }> {
  const db = await openGateQueueDb();
  const tx = db.transaction(META_STORE, 'readwrite');
  const store = tx.objectStore(META_STORE);
  const existing = await requestValue(store.get('device')) as DeviceRecord | undefined;
  const record: DeviceRecord = existing ?? {
    id: 'device', deviceId: randomId(), generationId: randomId(), sequence: 0,
  };
  if (!existing) store.put(record);
  await transactionDone(tx);
  return { deviceId: record.deviceId, generationId: record.generationId, sequence: record.sequence };
}

async function nextDeviceSequence(): Promise<{ deviceId: string; generationId: string; sequence: number }> {
  const db = await openGateQueueDb();
  const tx = db.transaction(META_STORE, 'readwrite');
  const store = tx.objectStore(META_STORE);
  const existing = await requestValue(store.get('device')) as DeviceRecord | undefined;
  const record: DeviceRecord = existing ?? {
    id: 'device', deviceId: randomId(), generationId: randomId(), sequence: 0,
  };
  record.sequence += 1;
  store.put(record);
  await transactionDone(tx);
  return { deviceId: record.deviceId, generationId: record.generationId, sequence: record.sequence };
}

async function readBlobBytes(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === 'function') return blob.arrayBuffer();
  if (typeof FileReader === 'undefined') {
    throw new Error('This browser cannot read the selected visitor photo for integrity verification.');
  }
  return new Promise<ArrayBuffer>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error('Unable to read visitor photo.'));
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) resolve(reader.result);
      else reject(new Error('Visitor photo read did not return binary data.'));
    };
    reader.readAsArrayBuffer(blob);
  });
}

export async function sha256Blob(blob: Blob): Promise<string> {
  if (!globalThis.crypto?.subtle) throw new Error('Secure photo hashing is unavailable in this browser.');
  const digest = await globalThis.crypto.subtle.digest('SHA-256', await readBlobBytes(blob));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
}

export async function queueVisitorPhoto(input: {
  userId: string;
  gateId: string;
  flatId: string;
  visitorName: string;
  purpose: string;
  phone?: string;
  photo: Blob;
  timeAnchor: SignedTimeAnchor;
  preApprovalCredential?: string;
  now?: number;
}): Promise<GateQueueEntry> {
  if (!input.photo.size || input.photo.size > 5 * 1024 * 1024) {
    throw new Error('Visitor photo must be between 1 byte and 5 MB.');
  }
  const deviceIdentity = await getGateDeviceIdentity();
  if (
    !input.timeAnchor
    || input.timeAnchor.payload.user_id !== input.userId
    || input.timeAnchor.payload.gate_id !== input.gateId
    || input.timeAnchor.payload.device_id !== deviceIdentity.deviceId
    || input.timeAnchor.payload.device_generation_id !== deviceIdentity.generationId
  ) {
    throw new Error('A signed time anchor for this guard, gate and enrolled device is required before saving offline.');
  }
  const storage = await requestPersistentGateStorage();
  if (storage.lowSpace) throw new Error('Persistent gate storage is unavailable, not granted or low on space. Connect to a managed device or free storage before capturing a visitor.');
  const device = await nextDeviceSequence();
  const now = input.now ?? Date.now();
  const elapsedSeconds = Math.max(0, Math.floor((now - input.timeAnchor.device_time_at_receipt) / 1000));
  const captureTime = new Date((input.timeAnchor.payload.timestamp_unix + elapsedSeconds) * 1000).toISOString();
  const record: GateQueueEntry = {
    eventUuid: randomId(),
    photoUuid: randomId(),
    gateId: input.gateId,
    deviceId: device.deviceId,
    deviceGenerationId: device.generationId,
    deviceSequence: device.sequence,
    captureTime,
    visitorName: input.visitorName,
    flatId: input.flatId,
    purpose: input.purpose,
    phone: input.phone,
    preApprovalCredential: input.preApprovalCredential,
    photoBlob: input.photo,
    mimeType: input.photo.type || 'application/octet-stream',
    size: input.photo.size,
    sha256: await sha256Blob(input.photo),
    timeAnchor: input.timeAnchor,
    status: 'PENDING',
    retryCount: 0,
    nextRetryAt: 0,
    createdAt: now,
  };

  const db = await openGateQueueDb();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  tx.objectStore(QUEUE_STORE).add(record);
  await transactionDone(tx);

  const saved = await getGateQueueEntry(record.eventUuid);
  if (!saved?.photoBlob || await sha256Blob(saved.photoBlob) !== saved.sha256) {
    await removeGateQueueEntry(record.eventUuid);
    throw new Error('Visitor photo could not be read back and verified. Capture the photo again.');
  }
  return saved;
}

export async function getGateQueueEntry(eventUuid: string): Promise<GateQueueEntry | undefined> {
  const db = await openGateQueueDb();
  const tx = db.transaction(QUEUE_STORE, 'readonly');
  const record = await requestValue(tx.objectStore(QUEUE_STORE).get(eventUuid)) as GateQueueEntry | undefined;
  await transactionDone(tx);
  return record;
}

export async function listGateQueueEntries(): Promise<GateQueueEntry[]> {
  const db = await openGateQueueDb();
  const tx = db.transaction(QUEUE_STORE, 'readonly');
  const records = await requestValue(tx.objectStore(QUEUE_STORE).getAll()) as GateQueueEntry[];
  await transactionDone(tx);
  return records.sort((a, b) => a.createdAt - b.createdAt);
}

export async function removeGateQueueEntry(eventUuid: string): Promise<void> {
  const db = await openGateQueueDb();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  tx.objectStore(QUEUE_STORE).delete(eventUuid);
  await transactionDone(tx);
}

export async function acknowledgeGateQueueEntry(eventUuid: string): Promise<void> {
  const record = await getGateQueueEntry(eventUuid);
  if (!record) return;
  const db = await openGateQueueDb();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  tx.objectStore(QUEUE_STORE).put({
    ...record,
    visitorName: '',
    flatId: '',
    purpose: '',
    phone: undefined,
    preApprovalCredential: undefined,
    photoBlob: null,
    status: 'ACKNOWLEDGED',
    lastError: undefined,
  });
  await transactionDone(tx);
}

export async function recordGateSyncFailure(eventUuid: string, message: string, now = Date.now()): Promise<void> {
  const record = await getGateQueueEntry(eventUuid);
  if (!record || !record.photoBlob) return;
  const retryCount = record.retryCount + 1;
  const delay = Math.min(5 * 60 * 1000, 1000 * (2 ** Math.min(retryCount, 8)));
  const db = await openGateQueueDb();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  tx.objectStore(QUEUE_STORE).put({
    ...record, status: 'RETRY', retryCount, nextRetryAt: now + delay, lastError: message,
  });
  await transactionDone(tx);
}

export async function expireOldGatePhotos(now = Date.now()): Promise<number> {
  const records = await listGateQueueEntries();
  const db = await openGateQueueDb();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  let expired = 0;
  for (const record of records) {
    const tooOld = now - new Date(record.captureTime).getTime() >= PHOTO_MAX_AGE_MS;
    if (record.photoBlob && tooOld && record.status !== 'ACKNOWLEDGED') {
      tx.objectStore(QUEUE_STORE).put({
        ...record,
        visitorName: '',
        flatId: '',
        purpose: '',
        phone: undefined,
        preApprovalCredential: undefined,
        photoBlob: null,
        status: 'EXPIRED',
        lastError: 'Photo exceeded 90-day retention.',
      });
      expired += 1;
    }
  }
  await transactionDone(tx);
  return expired;
}

export async function getGateQueueSummary(now = Date.now()): Promise<{ pendingCount: number; oldestAgeMs: number; failedCount: number }> {
  const records = await listGateQueueEntries();
  const pending = records.filter((r) => r.status === 'PENDING' || r.status === 'RETRY');
  const oldest = pending.length ? Math.min(...pending.map((r) => new Date(r.captureTime).getTime())) : now;
  return {
    pendingCount: pending.length,
    oldestAgeMs: pending.length ? Math.max(0, now - oldest) : 0,
    failedCount: pending.filter((r) => r.status === 'RETRY').length,
  };
}

export async function clearGateQueueForTests(): Promise<void> {
  const db = await openGateQueueDb();
  const tx = db.transaction([QUEUE_STORE, META_STORE], 'readwrite');
  tx.objectStore(QUEUE_STORE).clear();
  tx.objectStore(META_STORE).clear();
  await transactionDone(tx);
}
