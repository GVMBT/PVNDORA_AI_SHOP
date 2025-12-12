/**
 * LeaderboardConnected
 * 
 * Connected version of Leaderboard component with real API data.
 */

import React, { useEffect, useState } from 'react';
import Leaderboard from './Leaderboard';
import { useLeaderboardTyped } from '../../hooks/useApiTyped';

interface LeaderboardConnectedProps {
  onBack: () => void;
}

const LeaderboardConnected: React.FC<LeaderboardConnectedProps> = ({ onBack }) => {
  const { leaderboard, getLeaderboard, loading, error } = useLeaderboardTyped();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      await getLeaderboard();
      setIsInitialized(true);
    };
    init();
  }, [getLeaderboard]);

  // Loading state
  if (!isInitialized || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Loading Leaderboard...
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠</div>
          <div className="font-mono text-sm text-red-400 mb-2">CONNECTION_ERROR</div>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            onClick={() => getLeaderboard()}
            className="mt-6 px-6 py-2 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase hover:bg-white/20 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Leaderboard
      leaderboardData={leaderboard}
      onBack={onBack}
    />
  );
};

export default LeaderboardConnected;
