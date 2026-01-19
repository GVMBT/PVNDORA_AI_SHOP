/**
 * ProfileNetwork Component
 *
 * Displays referral network tree with line filtering.
 */

import { Crown, GitBranch, Network, User } from "lucide-react";
import type React from "react";
import { memo } from "react";
import { useLocale } from "../../hooks/useLocale";
import { formatPrice } from "../../utils/currency";
import type { NetworkNodeData } from "./types";

// Type alias for network line
type NetworkLine = 1 | 2 | 3;

// Helper functions to avoid nested ternaries
const getNodeAvatarContent = (node: NetworkNodeData) => {
  if (node.photoUrl) {
    return <img alt={node.handle} className="h-full w-full object-cover" src={node.photoUrl} />;
  }
  if (node.status === "VIP") {
    return <Crown className="text-yellow-500" size={14} />;
  }
  return <User className="text-gray-400" size={14} />;
};

const getRankBadgeClasses = (rank?: string): string => {
  if (rank === "ARCHITECT") {
    return "border-yellow-500 text-yellow-500";
  }
  if (rank === "OPERATOR") {
    return "border-purple-500 text-purple-500";
  }
  return "border-gray-500 text-gray-500";
};

interface ProfileNetworkProps {
  nodes: NetworkNodeData[];
  networkLine: 1 | 2 | 3;
  currency?: string;
  exchangeRate?: number;
  onLineChange: (line: 1 | 2 | 3) => void;
  onNodeClick: (id: string | number) => void;
}

const ProfileNetwork: React.FC<ProfileNetworkProps> = ({
  nodes,
  networkLine,
  currency = "USD",
  exchangeRate = 1,
  onLineChange,
  onNodeClick,
}) => {
  const { t } = useLocale();

  const displayedNodes = nodes.filter((n) => {
    const nodeWithLine = n as NetworkNodeData & { line?: number };
    return nodeWithLine.line === networkLine || !("line" in nodeWithLine);
  });

  return (
    <div className="border border-white/10 bg-[#050505] shadow-[0_0_50px_rgba(0,0,0,0.5)]">
      <div className="flex items-center justify-between gap-6 overflow-x-auto border-white/10 border-b bg-[#0a0a0a] p-2 px-4">
        {/* Title - left side */}
        <div className="flex items-center gap-2 whitespace-nowrap font-bold font-mono text-[10px] text-pandora-cyan text-sm uppercase tracking-widest">
          <GitBranch size={14} /> {t("profile.network.scanner")}
        </div>

        {/* Network Level Filter - right side */}
        <div className="flex items-center overflow-hidden rounded-sm border border-white/10 bg-[#050505]">
          {[1, 2, 3].map((line) => (
            <button
              className={`whitespace-nowrap border-white/10 border-r px-4 py-1.5 font-bold font-mono text-[9px] uppercase transition-colors last:border-0 hover:bg-white/5 ${
                networkLine === line ? "bg-pandora-cyan/20 text-pandora-cyan" : "text-gray-500"
              }`}
              key={line}
              onClick={() => onLineChange(line as NetworkLine)}
              type="button"
            >
              {t("profile.network.lineLabel").replace("{line}", line.toString())}
            </button>
          ))}
        </div>
      </div>

      <div className="p-0 font-mono text-xs">
        <div className="relative min-h-[300px]">
          {/* Vertical Connection Line */}
          <div className="absolute top-0 bottom-0 left-6 z-0 w-px bg-gradient-to-b from-pandora-cyan/30 via-white/5 to-transparent" />

          {displayedNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-600">
              <Network className="mb-2 opacity-20" size={24} />
              <span className="text-[10px] uppercase tracking-widest">
                {t("profile.network.noData").replace("{line}", networkLine.toString())}
              </span>
            </div>
          ) : (
            displayedNodes.map((node) => {
              const profitValue = (node.profit || node.earned || 0) * exchangeRate;

              return (
                <div
                  className="group relative border-white/5 border-b py-4 pr-4 pl-12 transition-colors hover:bg-white/[0.02]"
                  key={node.id}
                >
                  {/* Node Connector Dot */}
                  <div className="absolute top-8 left-[21px] z-10 box-content h-1.5 w-1.5 rounded-full border border-pandora-cyan bg-[#050505]" />
                  {/* Horizontal Connector Line */}
                  <div className="absolute top-9 left-6 h-px w-6 bg-white/10 transition-colors group-hover:bg-pandora-cyan/50" />

                  <button
                    className={`relative w-full cursor-pointer overflow-hidden rounded-sm border border-white/10 bg-[#0a0a0a] p-4 text-left transition-all duration-300 hover:border-pandora-cyan/50 hover:shadow-[0_0_15px_rgba(0,255,255,0.1)] ${node.status === "VIP" ? "border-l-2 border-l-yellow-500" : ""}
                    `}
                    onClick={() => onNodeClick(node.id)}
                    type="button"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-sm bg-white/5">
                          {getNodeAvatarContent(node)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            {node.handle.startsWith("@") ? (
                              <a
                                className="font-bold text-sm text-white transition-colors hover:text-pandora-cyan"
                                href={`https://t.me/${node.handle.slice(1)}`}
                                onClick={(e) => e.stopPropagation()}
                                rel="noopener noreferrer"
                                target="_blank"
                              >
                                {node.handle}
                              </a>
                            ) : (
                              <span className="font-bold text-sm text-white">{node.handle}</span>
                            )}
                            {node.rank && (
                              <span
                                className={`rounded-sm border px-1 text-[8px] ${getRankBadgeClasses(node.rank)}`}
                              >
                                {node.rank}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-[9px] text-gray-600">
                            <span>ID: #{node.id}</span>
                            {node.invitedBy && (
                              <>
                                <span>&bull;</span>
                                <span className="text-gray-500">UPLINK: {node.invitedBy}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-pandora-cyan text-xs">
                          +{formatPrice(profitValue, currency)}
                        </div>
                        <div className="text-[9px] text-gray-500 uppercase tracking-tighter">
                          {t("profile.network.commission")}
                        </div>
                      </div>
                    </div>
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(ProfileNetwork);
