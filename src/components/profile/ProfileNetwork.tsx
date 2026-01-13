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

// Helper functions to avoid nested ternaries
const getNodeAvatarContent = (node: NetworkNodeData) => {
  if (node.photoUrl) {
    return <img src={node.photoUrl} alt={node.handle} className="w-full h-full object-cover" />;
  }
  if (node.status === "VIP") {
    return <Crown size={14} className="text-yellow-500" />;
  }
  return <User size={14} className="text-gray-400" />;
};

const getRankBadgeClasses = (rank?: string): string => {
  if (rank === "ARCHITECT") return "border-yellow-500 text-yellow-500";
  if (rank === "OPERATOR") return "border-purple-500 text-purple-500";
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
      <div className="bg-[#0a0a0a] border-b border-white/10 p-2 px-4 flex items-center justify-between gap-6 overflow-x-auto">
        {/* Title - left side */}
        <div className="text-[10px] font-mono font-bold uppercase flex items-center gap-2 whitespace-nowrap text-pandora-cyan text-sm tracking-widest">
          <GitBranch size={14} /> {t("profile.network.scanner")}
        </div>

        {/* Network Level Filter - right side */}
        <div className="flex items-center bg-[#050505] border border-white/10 rounded-sm overflow-hidden">
          {[1, 2, 3].map((line) => (
            <button
              key={line}
              onClick={() => onLineChange(line as 1 | 2 | 3)}
              className={`px-4 py-1.5 text-[9px] font-mono font-bold border-r border-white/10 last:border-0 hover:bg-white/5 transition-colors uppercase whitespace-nowrap ${
                networkLine === line ? "bg-pandora-cyan/20 text-pandora-cyan" : "text-gray-500"
              }`}
            >
              {t("profile.network.lineLabel").replace("{line}", line.toString())}
            </button>
          ))}
        </div>
      </div>

      <div className="p-0 font-mono text-xs">
        <div className="relative min-h-[300px]">
          {/* Vertical Connection Line */}
          <div className="absolute top-0 bottom-0 left-6 w-px bg-gradient-to-b from-pandora-cyan/30 via-white/5 to-transparent z-0" />

          {displayedNodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-600">
              <Network size={24} className="mb-2 opacity-20" />
              <span className="uppercase tracking-widest text-[10px]">
                {t("profile.network.noData").replace("{line}", networkLine.toString())}
              </span>
            </div>
          ) : (
            displayedNodes.map((node) => {
              const profitValue = (node.profit || node.earned || 0) * exchangeRate;

              return (
                <div
                  key={node.id}
                  className="relative pl-12 pr-4 py-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors group"
                >
                  {/* Node Connector Dot */}
                  <div className="absolute left-[21px] top-8 w-1.5 h-1.5 rounded-full bg-[#050505] border border-pandora-cyan z-10 box-content" />
                  {/* Horizontal Connector Line */}
                  <div className="absolute left-6 top-9 w-6 h-px bg-white/10 group-hover:bg-pandora-cyan/50 transition-colors" />

                  <button
                    type="button"
                    onClick={() => onNodeClick(node.id)}
                    className={`
                      bg-[#0a0a0a] border border-white/10 hover:border-pandora-cyan/50 hover:shadow-[0_0_15px_rgba(0,255,255,0.1)] 
                      transition-all duration-300 rounded-sm p-4 relative overflow-hidden cursor-pointer text-left w-full
                      ${node.status === "VIP" ? "border-l-2 border-l-yellow-500" : ""}
                    `}
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-white/5 flex items-center justify-center rounded-sm overflow-hidden">
                          {getNodeAvatarContent(node)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            {node.handle.startsWith("@") ? (
                              <a
                                href={`https://t.me/${node.handle.slice(1)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-bold text-white text-sm hover:text-pandora-cyan transition-colors"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {node.handle}
                              </a>
                            ) : (
                              <span className="font-bold text-white text-sm">{node.handle}</span>
                            )}
                            {node.rank && (
                              <span
                                className={`text-[8px] px-1 rounded-sm border ${getRankBadgeClasses(node.rank)}`}
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
                        <div className="text-xs font-bold text-pandora-cyan">
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
