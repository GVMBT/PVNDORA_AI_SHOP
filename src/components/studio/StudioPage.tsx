import type React from "react";
import { useEffect, useState } from "react";
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

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const fetchedProfile = await getProfile();
        if (fetchedProfile) {
          // Check if user is admin
          setIsAdmin(fetchedProfile.role === "ADMIN");
        }
      } finally {
        setIsLoading(false);
      }
    };
    loadProfile();
  }, [getProfile]);

  // Loading state
  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black text-white flex items-center justify-center font-mono z-50">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan/30 border-t-pandora-cyan rounded-full animate-spin mx-auto mb-4" />
          <div className="text-xs text-gray-500 tracking-wider">LOADING_STUDIO...</div>
        </div>
      </div>
    );
  }

  // Access denied - not admin
  if (!isAdmin) {
    return (
      <div className="fixed inset-0 bg-black text-white flex items-center justify-center font-mono z-50">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="mb-8">
            <div className="w-20 h-20 mx-auto mb-4 border-2 border-yellow-500/30 rounded-full flex items-center justify-center">
              <svg
                className="w-12 h-12 text-yellow-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-label="Warning"
              >
                <title>Warning</title>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-white mb-4">STUDIO IS IN BETA</h1>
          </div>

          <div className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg p-6 mb-6">
            <h2 className="text-xl text-yellow-400 font-bold mb-4">🔒 Access Restricted</h2>
            <p className="text-gray-300 mb-6 leading-relaxed">
              Studio находится в закрытой бете. Доступ ограничен администраторами.
            </p>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-3 p-3 bg-white/5 rounded border border-white/10">
                <div className="w-8 h-8 bg-yellow-500/20 rounded-full flex items-center justify-center">
                  <svg
                    className="w-5 h-5 text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-label="Check"
                  >
                    <title>Check</title>
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0"
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
            type="button"
            onClick={onNavigateHome}
            className="px-6 py-3 bg-white/10 hover:bg-white/20 text-white border border-white/20 hover:border-white/40 rounded-lg transition-all duration-200 font-mono text-sm"
          >
            ← Вернуться назад
          </button>
        </div>

        {/* Background effect */}
        <div className="fixed inset-0 pointer-events-none -z-10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,_rgba(255,255,0,0.1)_0%,_rgba(0,0,0,0)_60%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] opacity-20" />
        </div>
      </div>
    );
  }

  // Admin access granted - show Studio
  return (
    <StudioContainer
      userBalance={profile?.balance || 0}
      onNavigateHome={onNavigateHome}
      onTopUp={onTopUp}
    />
  );
};

export default StudioPage;
