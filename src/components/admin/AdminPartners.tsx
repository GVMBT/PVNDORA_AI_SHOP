/**
 * AdminPartners Component
 * 
 * Partners and VIP management view.
 */

import React, { useState, memo } from 'react';
import { Edit } from 'lucide-react';
import StatusBadge from './StatusBadge';
import type { UserData } from './types';

interface AdminPartnersProps {
  partners: UserData[];
  onEditPartner: (partner: UserData) => void;
}

type PartnerTab = 'list' | 'requests';

const AdminPartners: React.FC<AdminPartnersProps> = ({
  partners,
  onEditPartner,
}) => {
  const [activeTab, setActiveTab] = useState<PartnerTab>('list');

  return (
    <div className="space-y-6">
      <div className="flex gap-4 border-b border-white/10 pb-1 overflow-x-auto">
        <button 
          onClick={() => setActiveTab('list')}
          className={`text-xs font-bold uppercase pb-2 px-2 transition-colors ${
            activeTab === 'list' 
              ? 'text-pandora-cyan border-b-2 border-pandora-cyan' 
              : 'text-gray-500'
          }`}
        >
          Partner List
        </button>
        <button 
          onClick={() => setActiveTab('requests')}
          className={`text-xs font-bold uppercase pb-2 px-2 transition-colors ${
            activeTab === 'requests' 
              ? 'text-pandora-cyan border-b-2 border-pandora-cyan' 
              : 'text-gray-500'
          }`}
        >
          VIP Requests <span className="ml-1 bg-red-500 text-white px-1 rounded-sm text-[9px]">0</span>
        </button>
      </div>

      {activeTab === 'list' ? (
        <>
          <div className="bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden hidden md:block">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-white/5 text-gray-400 uppercase">
                <tr>
                  <th className="p-4">Handle</th>
                  <th className="p-4">Rank</th>
                  <th className="p-4">Earnings</th>
                  <th className="p-4">Reward Mode</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-gray-300">
                {partners.map(p => (
                  <tr key={p.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4 font-bold text-white">{p.handle || p.username}</td>
                    <td className="p-4">
                      <span className={`text-[10px] px-2 py-0.5 border ${
                        p.level === 'ARCHITECT' 
                          ? 'border-yellow-500 text-yellow-500' 
                          : 'border-gray-500 text-gray-500'
                      }`}>
                        {p.level || 'USER'}
                      </span>
                    </td>
                    <td className="p-4 text-pandora-cyan">₽ {p.earned || 0}</td>
                    <td className="p-4 text-[10px] uppercase text-gray-400">
                      {p.rewardType === 'commission' ? '💰 Commission' : '🎁 Ref Discount'}
                    </td>
                    <td className="p-4">
                      <StatusBadge status={p.status || 'ACTIVE'} />
                    </td>
                    <td className="p-4">
                      <button 
                        onClick={() => onEditPartner(p)} 
                        className="hover:text-pandora-cyan"
                      >
                        <Edit size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Mobile Partners */}
          <div className="md:hidden space-y-4">
            {partners.map(p => (
              <div key={p.id} className="bg-[#0e0e0e] border border-white/10 p-4 relative">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-bold text-white">{p.handle || p.username}</span>
                  <StatusBadge status={p.status || 'ACTIVE'} />
                </div>
                <div className="text-xs text-gray-500 mb-2">
                  {p.level || 'USER'} • Earned: {p.earned || 0} ₽
                </div>
                <button 
                  onClick={() => onEditPartner(p)} 
                  className="w-full text-[10px] bg-white/5 py-2 hover:bg-pandora-cyan hover:text-black transition-colors"
                >
                  MANAGE
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {/* VIP Requests - empty for now */}
          <div className="text-center text-gray-500 text-xs py-8">
            No pending VIP requests
          </div>
        </div>
      )}
    </div>
  );
};

export default memo(AdminPartners);












