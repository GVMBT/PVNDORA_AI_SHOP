/**
 * Telegram WebApp SDK Type Definitions
 * 
 * Complete type definitions for Telegram Mini Apps WebApp API
 * Based on: https://core.telegram.org/bots/webapps
 */

declare global {
  interface Window {
    Telegram?: TelegramWebApp;
  }
}

export interface TelegramWebApp {
  WebApp: WebApp;
}

export interface WebApp {
  // Initialization
  initData: string;
  initDataUnsafe: WebAppInitData;
  version: string;
  platform: string;
  
  // Appearance
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  
  // State
  headerColor: string;
  backgroundColor: string;
  isClosingConfirmationEnabled: boolean;
  
  // Methods
  ready(): void;
  expand(): void;
  close(): void;
  sendData(data: string): void;
  openLink(url: string, options?: { try_instant_view?: boolean }): void;
  openTelegramLink(url: string): void;
  openInvoice(url: string, callback?: (status: string) => void): void;
  shareMessage(messageId: string, callback?: () => void): void;
  switchInlineQuery(query: string, chatTypes?: string[]): void;
  showPopup(params: PopupParams, callback?: (id: string) => void): void;
  showAlert(message: string, callback?: () => void): void;
  showConfirm(message: string, callback?: (confirmed: boolean) => void): void;
  showScanQrPopup(params: ScanQrPopupParams, callback?: (text: string) => void): void;
  closeScanQrPopup(): void;
  readTextFromClipboard(callback?: (text: string) => void): void;
  requestWriteAccess(callback?: (granted: boolean) => void): void;
  requestContact(callback?: (granted: boolean) => void): void;
  
  // Events
  onEvent(eventType: string, eventHandler: () => void): void;
  offEvent(eventType: string, eventHandler: () => void): void;
  
  // Main Button
  MainButton: MainButton;
  
  // Back Button
  BackButton: BackButton;
  
  // Settings Button
  SettingsButton: SettingsButton;
  
  // Haptic Feedback
  HapticFeedback: HapticFeedback;
  
  // Cloud Storage
  CloudStorage: CloudStorage;
  
  // Biometric Manager
  BiometricManager: BiometricManager;
  
  // Utils
  isVersionAtLeast(version: string): boolean;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  enableClosingConfirmation(): void;
  disableClosingConfirmation(): void;
  enableVerticalSwipes(): void;
  disableVerticalSwipes(): void;
}

export interface WebAppInitData {
  query_id?: string;
  user?: WebAppUser;
  receiver?: WebAppUser;
  chat?: WebAppChat;
  chat_type?: string;
  chat_instance?: string;
  start_param?: string;
  can_send_after?: number;
  auth_date: number;
  hash: string;
}

export interface WebAppUser {
  id: number;
  is_bot: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
  added_to_attachment_menu?: boolean;
  allows_write_to_pm?: boolean;
}

export interface WebAppChat {
  id: number;
  type: 'group' | 'supergroup' | 'channel';
  title: string;
  username?: string;
  photo_url?: string;
}

export interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
  header_bg_color?: string;
  accent_text_color?: string;
  section_bg_color?: string;
  section_header_text_color?: string;
  subtitle_text_color?: string;
  destructive_text_color?: string;
}

export interface PopupParams {
  title?: string;
  message: string;
  buttons?: PopupButton[];
}

export interface PopupButton {
  id?: string;
  type?: 'default' | 'ok' | 'close' | 'cancel' | 'destructive';
  text?: string;
}

export interface ScanQrPopupParams {
  text?: string;
}

export interface MainButton {
  text: string;
  color: string;
  textColor: string;
  isVisible: boolean;
  isActive: boolean;
  isProgressVisible: boolean;
  
  setText(text: string): void;
  onClick(callback: () => void): void;
  offClick(callback: () => void): void;
  show(): void;
  hide(): void;
  enable(): void;
  disable(): void;
  showProgress(leaveActive?: boolean): void;
  hideProgress(): void;
  setParams(params: MainButtonParams): void;
}

export interface MainButtonParams {
  text?: string;
  color?: string;
  text_color?: string;
  is_active?: boolean;
  is_visible?: boolean;
}

export interface BackButton {
  isVisible: boolean;
  
  onClick(callback: () => void): void;
  offClick(callback: () => void): void;
  show(): void;
  hide(): void;
}

export interface SettingsButton {
  isVisible: boolean;
  
  onClick(callback: () => void): void;
  offClick(callback: () => void): void;
  show(): void;
  hide(): void;
}

export interface HapticFeedback {
  impactOccurred(style: HapticStyle): void;
  notificationOccurred(type: HapticNotificationType): void;
  selectionChanged(): void;
}

export type HapticStyle = 'light' | 'medium' | 'heavy' | 'rigid' | 'soft';
export type HapticNotificationType = 'error' | 'success' | 'warning';

export interface CloudStorage {
  setItem(key: string, value: string, callback?: (error: Error | null, success: boolean) => void): void;
  getItem(key: string, callback: (error: Error | null, value: string | null) => void): void;
  getItems(keys: string[], callback: (error: Error | null, values: Record<string, string>) => void): void;
  removeItem(key: string, callback?: (error: Error | null, success: boolean) => void): void;
  removeItems(keys: string[], callback?: (error: Error | null, success: boolean) => void): void;
  getKeys(callback: (error: Error | null, keys: string[]) => void): void;
}

export interface BiometricManager {
  isInited: boolean;
  isBiometricAvailable: boolean;
  biometricType: 'finger' | 'face' | 'unknown';
  isAccessRequested: boolean;
  isAccessGranted: boolean;
  token: string | null;
  
  init(callback?: (success: boolean) => void): void;
  requestAccess(params: BiometricRequestAccessParams, callback?: (success: boolean, token?: string) => void): void;
  authenticate(params: BiometricAuthenticateParams, callback?: (success: boolean, token?: string) => void): void;
  updateBiometricToken(token: string, callback?: (success: boolean) => void): void;
  openSettings(): void;
}

export interface BiometricRequestAccessParams {
  reason?: string;
}

export interface BiometricAuthenticateParams {
  reason?: string;
}

export {};















