import type { MMKV } from 'react-native-mmkv';
import { createMMKV } from 'react-native-mmkv';

export type StorageInstance = {
  getString: (key: string) => string | undefined;
  getBoolean: (key: string) => boolean | undefined;
  getNumber: (key: string) => number | undefined;
  getBuffer: (key: string) => ArrayBuffer | undefined;
  set: (key: string, value: boolean | string | number | ArrayBuffer) => void;
  remove: (key: string) => void;
  delete: (key: string) => void;
  contains: (key: string) => boolean;
  clearAll: () => void;
  getAllKeys: () => string[];
  addOnValueChangedListener: (onValueChanged: (key: string) => void) => { remove: () => void };
};

function createFallbackStorage(): StorageInstance {
  const memory = new Map<string, string>();
  const listeners = new Set<(key: string) => void>();

  return {
    getString: (key: string) => memory.get(key),
    getBoolean: (key: string) => {
      const val = memory.get(key);
      if (val === undefined)
        return undefined;
      return val === 'true';
    },
    getNumber: (key: string) => {
      const val = memory.get(key);
      if (val === undefined)
        return undefined;
      const num = Number(val);
      return Number.isNaN(num) ? undefined : num;
    },
    getBuffer: () => undefined,
    set: (key: string, value: boolean | string | number | ArrayBuffer) => {
      memory.set(key, String(value));
      listeners.forEach((listener) => {
        try {
          listener(key);
        }
        catch {}
      });
    },
    remove: (key: string) => {
      memory.delete(key);
      listeners.forEach((listener) => {
        try {
          listener(key);
        }
        catch {}
      });
    },
    delete: (key: string) => {
      memory.delete(key);
      listeners.forEach((listener) => {
        try {
          listener(key);
        }
        catch {}
      });
    },
    contains: (key: string) => memory.has(key),
    clearAll: () => {
      memory.clear();
    },
    getAllKeys: () => Array.from(memory.keys()),
    addOnValueChangedListener: (onValueChanged: (key: string) => void) => {
      listeners.add(onValueChanged);
      return {
        remove: () => {
          listeners.delete(onValueChanged);
        },
      };
    },
  };
}

function initStorage(): MMKV {
  try {
    return createMMKV();
  }
  catch (error) {
    console.warn(
      '[storage] NitroModules/MMKV native module not found in this client. Using fallback storage. (Rebuild native app via "pnpm expo run:ios" or "run:android" for native MMKV persistence).',
      error,
    );
    return createFallbackStorage() as unknown as MMKV;
  }
}

export const storage: MMKV = initStorage();

export function getItem<T>(key: string): T | null {
  try {
    const value = storage.getString(key);
    return value ? JSON.parse(value) || null : null;
  }
  catch {
    return null;
  }
}

export async function setItem<T>(key: string, value: T) {
  try {
    storage.set(key, JSON.stringify(value));
  }
  catch {}
}

export async function removeItem(key: string) {
  try {
    storage.remove(key);
  }
  catch {}
}
