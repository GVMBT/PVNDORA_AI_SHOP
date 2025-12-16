/**
 * ProfileBilling Component
 * 
 * Displays billing logs and transaction history.
 */

import React, { memo } from 'react';
import type { BillingLogData } from './types';

interface ProfileBillingProps {
  logs: BillingLogData[];
}

const ProfileBilling: React.FC<ProfileBillingProps> = ({ logs }) => {
  return (
    <div className="border border-white/10 bg-[#050505] shadow-[0_0_50px_rgba(0,0,0,0.5)]">
      <div className="bg-[#0a0a0a] border-b border-white/10 p-2 px-4">
        <div className="text-[10px] font-mono font-bold uppercase text-pandora-cyan">
          SYSTEM_LOGS
        </div>
      </div>

      <div className="p-0 font-mono text-xs">
        <div className="divide-y divide-white/5">
          {logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-600">
              <span className="uppercase tracking-widest text-[10px]">NO_TRANSACTIONS</span>
            </div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="grid grid-cols-12 px-4 py-3 hover:bg-white/5 transition-colors">
                <div className="col-span-3 sm:col-span-2 text-gray-500">{log.id}</div>
                <div className="col-span-3 sm:col-span-2">
                  <span className={`px-1 text-[9px] border ${
                    log.type === 'INCOME' ? 'text-green-500 border-green-500/30' :
                    log.type === 'OUTCOME' ? 'text-blue-500 border-blue-500/30' :
                    'text-cyan-500 border-cyan-500/30'
                  }`}>
                    {log.type}
                  </span>
                </div>
                <div className="col-span-3 sm:col-span-4 text-gray-300 truncate">{log.source}</div>
                <div className="col-span-3 sm:col-span-4 text-right text-white font-bold">{log.amount}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(ProfileBilling);










