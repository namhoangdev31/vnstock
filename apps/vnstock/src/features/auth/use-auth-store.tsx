import type { TokenType, UserProfile } from '@/lib/auth/utils';

import { create } from 'zustand';
import {
  getToken,
  getUserProfile,
  removeToken,
  removeUserProfile,
  setToken,
  setUserProfile,
} from '@/lib/auth/utils';
import { createSelectors } from '@/lib/utils';

type AuthState = {
  token: TokenType | null;
  user: UserProfile | null;
  status: 'idle' | 'signOut' | 'signIn';
  signIn: (data: TokenType, user?: UserProfile) => void;
  signOut: () => void;
  hydrate: () => void;
};

const _useAuthStore = create<AuthState>((set, get) => ({
  status: 'idle',
  token: null,
  user: null,
  signIn: (token, user) => {
    setToken(token);
    if (user) {
      setUserProfile(user);
      set({ status: 'signIn', token, user });
    }
    else {
      const existingUser = getUserProfile() ?? null;
      set({ status: 'signIn', token, user: existingUser });
    }
  },
  signOut: () => {
    removeToken();
    removeUserProfile();
    set({ status: 'signOut', token: null, user: null });
  },
  hydrate: () => {
    try {
      const userToken = getToken();
      if (userToken !== null) {
        const userProfile = getUserProfile() ?? undefined;
        get().signIn(userToken, userProfile);
      }
      else {
        get().signOut();
      }
    }
    catch (e) {
      // only to remove eslint error, handle the error properly
      console.error(e);
      // catch error here
      // Maybe sign_out user!
    }
  },
}));

export const useAuthStore = createSelectors(_useAuthStore);

export function signOut() {
  return _useAuthStore.getState().signOut();
}
export function signIn(token: TokenType, user?: UserProfile) {
  return _useAuthStore.getState().signIn(token, user);
}
export function hydrateAuth() {
  return _useAuthStore.getState().hydrate();
}
