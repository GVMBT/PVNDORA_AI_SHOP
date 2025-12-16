/**
 * ProfileHeader Component
 * 
 * User identity card with avatar, name, handle, and admin access button.
 */

import React, { memo } from 'react';
import { User, ArrowLeft, Crown, LayoutDashboard } from 'lucide-react';
import type { ProfileDataProp } from './types';

interface ProfileHeaderProps {
  user: ProfileDataProp;
  onBack: () => void;
  onAdminEnter?: () => void;
}

const ProfileHeader: React.FC<ProfileHeaderProps> = ({
  user,
  onBack,
  onAdminEnter,
}) => {
  return (
    <>
      {/* Unified Header */}
      <div className="mb-8 md:mb-16">
        <button 
          onClick={onBack} 
          className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors"
        >
          <ArrowLeft size={12} /> RETURN_TO_BASE
        </button>
        <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
          OPERATIVE <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white/50">PROFILE</span>
        </h1>
        <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan tracking-widest uppercase">
          <User size={12} />
          <span>User_Identity // Stats</span>
        </div>
      </div>

      {/* User Card / Identity */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-12 border-b border-white/10 pb-6">
        <div className="flex items-center gap-6">
          <div className="relative group">
            <div className="w-20 h-20 bg-black border border-white/20 flex items-center justify-center relative overflow-hidden rounded-sm">
              {user.photoUrl ? (
                <img src={user.photoUrl} alt={user.name} className="w-full h-full object-cover relative z-10" />
              ) : (
                <User size={40} className="text-gray-400 relative z-10" />
              )}
              <div className="absolute inset-0 bg-gradient-to-tr from-pandora-cyan/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="absolute top-0 w-full h-full bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
            </div>
            {/* Online Status Dot */}
            <div className="absolute bottom-1 right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-black animate-pulse" />
          </div>
          <div>
            <h2 className="text-2xl font-display font-bold text-white tracking-tight mb-1 flex items-center gap-2">
              {user.name}
              {user.isVip && <Crown size={18} className="text-yellow-500 fill-yellow-500/20" />}
            </h2>
            <div className="flex items-center gap-3 text-xs font-mono text-gray-500">
              <span>{user.handle}</span>
              <span className="text-pandora-cyan">//</span>
              <span>{user.id}</span>
              {user.role === 'ADMIN' && (
                <span className="text-red-500 font-bold bg-red-900/10 px-1 border border-red-500/30">
                  ROOT_ADMIN
                </span>
              )}
            </div>
          </div>
        </div>
        {/* Admin Entry */}
        {user.role === 'ADMIN' && (
          <button 
            onClick={onAdminEnter}
            className="flex items-center gap-2 bg-red-900/10 border border-red-500/30 text-red-500 px-4 py-2 hover:bg-red-500 hover:text-white transition-all text-xs font-mono font-bold uppercase tracking-widest"
          >
            <LayoutDashboard size={14} />
            ACCESS_ADMIN_PANEL
          </button>
        )}
      </div>
    </>
  );
};

export default memo(ProfileHeader);










