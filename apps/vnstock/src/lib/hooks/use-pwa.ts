import * as React from 'react';
import { Platform } from 'react-native';

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
};

declare global {
  // eslint-disable-next-line ts/consistent-type-definitions
  interface Window {
    __pwaInstallPrompt?: BeforeInstallPromptEvent | null;
  }
}

function checkIsStandalone(): boolean {
  if (Platform.OS !== 'web' || typeof window === 'undefined') {
    return false;
  }
  return (
    window.matchMedia('(display-mode: standalone)').matches
    || (window.navigator as unknown as { standalone?: boolean }).standalone === true
    || document.referrer.includes('android-app://')
  );
}

function checkHasInstallPrompt(): boolean {
  if (Platform.OS !== 'web' || typeof window === 'undefined') {
    return false;
  }
  return Boolean(window.__pwaInstallPrompt);
}

export function usePWA() {
  const [canInstall, setCanInstall] = React.useState(checkHasInstallPrompt);
  const [isInstalled, setIsInstalled] = React.useState(checkIsStandalone);
  const [hasUpdate, setHasUpdate] = React.useState(false);
  const installPromptRef = React.useRef<BeforeInstallPromptEvent | null>(null);

  React.useEffect(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined') {
      return;
    }

    if (window.__pwaInstallPrompt) {
      installPromptRef.current = window.__pwaInstallPrompt;
    }

    const handleInstallable = () => {
      if (window.__pwaInstallPrompt) {
        installPromptRef.current = window.__pwaInstallPrompt;
      }
      setCanInstall(true);
    };

    const handleInstalled = () => {
      installPromptRef.current = null;
      setIsInstalled(true);
      setCanInstall(false);
    };

    const handleUpdate = () => {
      setHasUpdate(true);
    };

    window.addEventListener('pwa-installable', handleInstallable);
    window.addEventListener('pwa-installed', handleInstalled);
    window.addEventListener('pwa-update-available', handleUpdate);

    return () => {
      window.removeEventListener('pwa-installable', handleInstallable);
      window.removeEventListener('pwa-installed', handleInstalled);
      window.removeEventListener('pwa-update-available', handleUpdate);
    };
  }, []);

  const installPWA = React.useCallback(async () => {
    const promptEvent = installPromptRef.current || (typeof window !== 'undefined' ? window.__pwaInstallPrompt : null);
    if (!promptEvent) {
      return false;
    }

    try {
      await promptEvent.prompt();
      const choice = await promptEvent.userChoice;
      if (choice.outcome === 'accepted') {
        installPromptRef.current = null;
        setCanInstall(false);
        return true;
      }
    }
    catch (err) {
      console.warn('PWA install prompt error:', err);
    }
    return false;
  }, []);

  const applyUpdate = React.useCallback(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined') {
      return;
    }

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistration().then((reg) => {
        if (reg && reg.waiting) {
          reg.waiting.postMessage({ type: 'SKIP_WAITING' });
        }
        window.location.reload();
      });
    }
    else {
      window.location.reload();
    }
  }, []);

  return {
    isWeb: Platform.OS === 'web',
    isInstalled,
    canInstall,
    hasUpdate,
    installPWA,
    applyUpdate,
  };
}
