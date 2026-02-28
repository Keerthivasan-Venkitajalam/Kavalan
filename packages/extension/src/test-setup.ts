/**
 * Test Setup
 * 
 * Global test configuration and mocks.
 */

import { vi } from 'vitest';

// Mock Chrome APIs
global.chrome = {
  runtime: {
    sendMessage: vi.fn(),
    onMessage: {
      addListener: vi.fn()
    },
    onInstalled: {
      addListener: vi.fn()
    }
  },
  storage: {
    local: {
      get: vi.fn(),
      set: vi.fn(),
      remove: vi.fn()
    }
  },
  tabs: {
    query: vi.fn(),
    remove: vi.fn()
  },
  notifications: {
    create: vi.fn()
  },
  action: {
    setBadgeText: vi.fn(),
    setBadgeBackgroundColor: vi.fn()
  }
} as any;

// Use Node.js Web Crypto API (available in Node 15+)
import { webcrypto } from 'crypto';

Object.defineProperty(global, 'crypto', {
  value: {
    subtle: webcrypto.subtle,
    getRandomValues: (arr: any) => webcrypto.getRandomValues(arr)
  }
});
