/**
 * Telegram WebApp Hook
 * 
 * Provides access to Telegram Mini App SDK features
 */
import { useEffect, useState, useCallback } from 'react';

// Get WebApp from global Telegram object
const tg = window.Telegram?.WebApp;

export function useTelegram() {
    const [isReady, setIsReady] = useState(false);
    const [user, setUser] = useState(null);
    const [initData, setInitData] = useState('');
    const [colorScheme, setColorScheme] = useState('dark');
    const [startParam, setStartParam] = useState(null);

    useEffect(() => {
        if (tg) {
            // Signal that app is ready
            tg.ready();
            tg.expand();
            
            setIsReady(true);
            setInitData(tg.initData || '');
            setColorScheme(tg.colorScheme || 'dark');
            
            // Parse user data
            if (tg.initDataUnsafe?.user) {
                setUser(tg.initDataUnsafe.user);
            }
            
            // Parse start parameter (e.g., product ID)
            if (tg.initDataUnsafe?.start_param) {
                setStartParam(tg.initDataUnsafe.start_param);
            }
            
            // Listen for theme changes
            tg.onEvent('themeChanged', () => {
                setColorScheme(tg.colorScheme);
            });
        }
    }, []);

    // Show/hide main button
    const showMainButton = useCallback((text, onClick) => {
        if (tg?.MainButton) {
            tg.MainButton.setText(text);
            tg.MainButton.show();
            tg.MainButton.onClick(onClick);
        }
    }, []);

    const hideMainButton = useCallback(() => {
        if (tg?.MainButton) {
            tg.MainButton.hide();
        }
    }, []);

    // Show/hide back button
    const showBackButton = useCallback((onClick) => {
        if (tg?.BackButton) {
            tg.BackButton.show();
            tg.BackButton.onClick(onClick);
        }
    }, []);

    const hideBackButton = useCallback(() => {
        if (tg?.BackButton) {
            tg.BackButton.hide();
        }
    }, []);

    // Close the Mini App
    const close = useCallback(() => {
        if (tg) {
            tg.close();
        }
    }, []);

    // Send data back to bot
    const sendData = useCallback((data) => {
        if (tg) {
            tg.sendData(JSON.stringify(data));
        }
    }, []);

    // Show popup
    const showPopup = useCallback((params) => {
        return new Promise((resolve) => {
            if (tg?.showPopup) {
                tg.showPopup(params, (buttonId) => {
                    resolve(buttonId);
                });
            } else {
                resolve(null);
            }
        });
    }, []);

    // Show alert
    const showAlert = useCallback((message) => {
        return new Promise((resolve) => {
            if (tg?.showAlert) {
                tg.showAlert(message, resolve);
            } else {
                alert(message);
                resolve();
            }
        });
    }, []);

    // Haptic feedback
    const hapticFeedback = useCallback((type = 'light') => {
        if (tg?.HapticFeedback) {
            if (type === 'success') {
                tg.HapticFeedback.notificationOccurred('success');
            } else if (type === 'error') {
                tg.HapticFeedback.notificationOccurred('error');
            } else if (type === 'warning') {
                tg.HapticFeedback.notificationOccurred('warning');
            } else {
                tg.HapticFeedback.impactOccurred(type);
            }
        }
    }, []);

    // Open link in browser
    const openLink = useCallback((url) => {
        if (tg?.openLink) {
            tg.openLink(url);
        } else {
            window.open(url, '_blank');
        }
    }, []);

    // Get auth header for API calls
    const getAuthHeader = useCallback(() => {
        return initData ? `tma ${initData}` : '';
    }, [initData]);

    return {
        isReady,
        user,
        initData,
        colorScheme,
        startParam,
        showMainButton,
        hideMainButton,
        showBackButton,
        hideBackButton,
        close,
        sendData,
        showPopup,
        showAlert,
        hapticFeedback,
        openLink,
        getAuthHeader,
        // Raw access to WebApp
        webApp: tg
    };
}

export default useTelegram;

