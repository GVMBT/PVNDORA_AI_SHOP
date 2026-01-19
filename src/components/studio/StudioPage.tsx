import type React from "react";
import { useEffect, useRef, useState } from "react";
import { useProfileTyped } from "../../hooks/useApiTyped";
import StudioContainer from "./StudioContainer";

interface StudioPageProps {
  onNavigateHome: () => void;
  onTopUp: () => void;
}

/**
 * Studio Page - AI Generation Interface
 *
 * Currently in beta, restricted to admins only.
 * Uses real user balance from profile API.
 */
const StudioPage: React.FC<StudioPageProps> = ({ onNavigateHome, onTopUp }) => {
  const { profile, getProfile } = useProfileTyped();
  const [isLoading, setIsLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const getProfileRef = useRef(getProfile);

  // Keep ref updated
  useEffect(() => {
    getProfileRef.current = getProfile;
  }, [getProfile]);

  // Load profile only once on mount to avoid infinite loop
  useEffect(() => {
    let cancelled = false;
    const loadProfile = async () => {
      try {
        const fetchedProfile = await getProfileRef.current();
        if (!cancelled && fetchedProfile) {
          // Check if user is admin
          setIsAdmin(fetchedProfile.role === "ADMIN");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    loadProfile();
    return () => {
      cancelled = true;
    };
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black font-mono text-white">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-2 border-pandora-cyan/30 border-t-pandora-cyan" />
          <div className="text-gray-500 text-xs tracking-wider">LOADING_STUDIO...</div>
        </div>
      </div>
    );
  }

  // Access denied - not admin
  if (!isAdmin) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black font-mono text-white">
        <div className="mx-auto max-w-md p-8 text-center">
          <div className="mb-8">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full border-2 border-yellow-500/30">
              <svg
                aria-label="Warning"
                className="h-12 w-12 text-yellow-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <title>Warning</title>
                <path
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                />
              </svg>
            </div>
            <h1 className="mb-4 font-bold text-3xl text-white">STUDIO IS IN BETA</h1>
          </div>

          <div className="mb-6 rounded-lg border border-white/10 bg-black/60 p-6 backdrop-blur-md">
            <h2 className="mb-4 font-bold text-xl text-yellow-400">🔒 Access Restricted</h2>
            <p className="mb-6 text-gray-300 leading-relaxed">
              Studio находится в закрытой бете. Доступ ограничен администраторами.
            </p>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-3 rounded border border-white/10 bg-white/5 p-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-yellow-500/20">
                  <svg
                    aria-label="Check"
                    className="h-5 w-5 text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <title>Check</title>
                    <path
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                    />
                  </svg>
                </div>
                <div>
                  <div className="font-bold text-white">Для администраторов</div>
                  <div className="text-gray-400 text-xs">Полный доступ к функциям генерации</div>
                </div>
              </div>
            </div>
          </div>

          <button
            className="rounded-lg border border-white/20 bg-white/10 px-6 py-3 font-mono text-sm text-white transition-all duration-200 hover:border-white/40 hover:bg-white/20"
            onClick={onNavigateHome}
            type="button"
          >
            ← Вернуться назад
          </button>
        </div>

        {/* Background effect */}
        <div className="pointer-events-none fixed inset-0 -z-10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,_rgba(255,255,0,0.1)_0%,_rgba(0,0,0,0)_60%)]" />
          <div className="absolute inset-0 bg-[length:100%_4px,3px_100%] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] opacity-20" />
        </div>
      </div>
    );
  }

  // Admin access granted - show Studio
  return (
    <StudioContainer
      onNavigateHome={onNavigateHome}
      onTopUp={onTopUp}
      userBalance={profile?.balance || 0}
    />
  );
};

export default StudioPage;
