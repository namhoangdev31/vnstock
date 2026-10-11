import { getItem, removeItem, setItem } from '@/lib/storage';

const TOKEN = 'token';
const USER_PROFILE = 'user_profile';

export type TokenType = {
  access: string;
  refresh: string;
};

export type UserProfile = {
  email: string;
  name: string;
  avatar?: string;
  provider: 'email' | 'google' | 'apple' | 'passkey' | 'guest';
};

export function getToken() {
  return getItem<TokenType>(TOKEN);
}
export function removeToken() {
  return removeItem(TOKEN);
}
export function setToken(value: TokenType) {
  return setItem<TokenType>(TOKEN, value);
}

export function getUserProfile() {
  return getItem<UserProfile>(USER_PROFILE);
}
export function removeUserProfile() {
  return removeItem(USER_PROFILE);
}
export function setUserProfile(value: UserProfile) {
  return setItem<UserProfile>(USER_PROFILE, value);
}
