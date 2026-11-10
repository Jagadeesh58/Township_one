import '@testing-library/jest-dom/vitest';
import { Blob as NodeBlob } from 'node:buffer';
import { webcrypto } from 'node:crypto';

// jsdom exposes randomUUID/getRandomValues but not SubtleCrypto; use Node's
// WebCrypto implementation so browser SHA-256 integrity paths are testable.
if (!globalThis.crypto?.subtle) {
  Object.defineProperty(globalThis, 'crypto', {
    configurable: true,
    value: webcrypto,
  });
}

// Ensure Node's native structuredClone-compatible Blob is available in jsdom
globalThis.Blob = NodeBlob as any;
if (typeof window !== 'undefined') {
  window.Blob = NodeBlob as any;
}

// Ensure jsdom's FileReader can read NodeBlob in legacy fallback tests
if (typeof FileReader !== 'undefined') {
  const origReadAsArrayBuffer = FileReader.prototype.readAsArrayBuffer;
  FileReader.prototype.readAsArrayBuffer = function (blob: any) {
    if (blob instanceof NodeBlob) {
      NodeBlob.prototype.arrayBuffer.call(blob).then((buf: ArrayBuffer) => {
        const TargetArrayBuffer = (typeof window !== 'undefined' && window.ArrayBuffer) ? window.ArrayBuffer : ArrayBuffer;
        const view = new Uint8Array(buf);
        const targetBuf = new TargetArrayBuffer(view.byteLength);
        new Uint8Array(targetBuf).set(view);
        Object.defineProperty(this, 'result', { configurable: true, value: targetBuf });
        this.onload?.(new ProgressEvent('load') as any);
      }).catch((err: any) => {
        Object.defineProperty(this, 'error', { configurable: true, value: err });
        this.onerror?.(new ProgressEvent('error') as any);
      });
      return;
    }
    return origReadAsArrayBuffer.call(this, blob);
  };
}
