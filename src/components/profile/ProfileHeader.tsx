/**
 * ProfileHeader Component
 *
 * User identity card with avatar, name, handle, and admin access button.
 */

import { ArrowLeft, Crown, LayoutDashboard, User } from "lucide-react";
import type React from "react";
import { memo } from "react";
import { useLocale } from "../../hooks/useLocale";
import type { ProfileDataProp } from "./types";

interface ProfileHeaderProps {
  user: ProfileDataProp;
  onBack: () => void;
  onAdminEnter?: () => void;
}

const ProfileHeader: React.FC<ProfileHeaderProps> = ({ user, onBack, onAdminEnter }) => {
  const { t, tEn } = useLocale();
  return (
    <>
      {/* Unified Header */}
      <div className="mb-8 md:mb-16">
        <button
          className="mb-4 flex items-center gap-2 font-mono text-[10px] text-gray-500 transition-colors hover:text-pandora-cyan"
          onClick={onBack}
          type="button"
        >
          <ArrowLeft size={12} /> {t("empty.returnToBase")}
        </button>
        <h1 className="mb-4 font-black font-display text-3xl text-white uppercase leading-[0.9] tracking-tighter sm:text-4xl md:text-6xl">
          {tEn("profile.header.pageTitlePrefix")} <br />{" "}
          <span className="bg-gradient-to-r from-pandora-cyan to-white/50 bg-clip-text text-transparent">
            {tEn("profile.header.pageTitle")}
          </span>
        </h1>
        <div className="flex items-center gap-2 font-mono text-[10px] text-pandora-cyan uppercase tracking-widest">
          <User size={12} />
          <span>User_Identity | Stats</span>
        </div>
      </div>

      {/* User Card / Identity */}
      <div className="mb-12 flex flex-col items-start justify-between gap-6 border-white/10 border-b pb-6 md:flex-row md:items-end">
        <div className="flex items-center gap-6">
          <div className="group relative">
            <div className="relative flex h-20 w-20 items-center justify-center overflow-hidden rounded-sm border border-white/20 bg-black">
              {user.photoUrl ? (
                <img
                  alt={user.name}
                  className="relative z-10 h-full w-full object-cover"
                  src={user.photoUrl}
                />
              ) : (
                <User className="relative z-10 text-gray-400" size={40} />
              )}
              <div className="absolute inset-0 bg-gradient-to-tr from-pandora-cyan/20 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div
                className="absolute top-0 h-full w-full opacity-20 mix-blend-overlay"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                }}
              />
            </div>
            {/* Online Status Dot */}
            <div className="absolute right-1 bottom-1 h-3 w-3 animate-pulse rounded-full border-2 border-black bg-green-500" />
          </div>
          <div>
            <h2 className="mb-1 flex items-center gap-2 font-bold font-display text-2xl text-white tracking-tight">
              {user.name}
              {user.isVip && <Crown className="fill-yellow-500/20 text-yellow-500" size={18} />}
            </h2>
            <div className="flex items-center gap-3 font-mono text-gray-500 text-xs">
              <span>{user.handle}</span>
              <span className="text-pandora-cyan">{"// "}</span>
              <span>{user.id}</span>
              {user.role === "ADMIN" && (
                <span className="border border-red-500/30 bg-red-900/10 px-1 font-bold text-red-500">
                  ROOT_ADMIN
                </span>
              )}
            </div>
          </div>
        </div>
        {/* Action Buttons */}
        <div className="flex flex-col gap-2 sm:flex-row">
          {/* Admin Entry */}
          {user.role === "ADMIN" && onAdminEnter && (
            <button
              className="flex items-center gap-2 border border-red-500/30 bg-red-900/10 px-4 py-2 font-bold font-mono text-red-500 text-xs uppercase tracking-widest transition-all hover:bg-red-500 hover:text-white"
              onClick={onAdminEnter}
              type="button"
            >
              <LayoutDashboard size={14} />
              ACCESS_ADMIN_PANEL
            </button>
          )}
        </div>
      </div>
    </>
  );
};

export default memo(ProfileHeader);
