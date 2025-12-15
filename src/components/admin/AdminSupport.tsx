/**
 * AdminSupport Component
 * 
 * Support tickets management view.
 */

import React, { useState, memo } from 'react';
import { MessageSquare, ArrowUpRight } from 'lucide-react';
import type { TicketData } from './types';

interface AdminSupportProps {
  tickets: TicketData[];
}

const AdminSupport: React.FC<AdminSupportProps> = ({ tickets }) => {
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
      {/* Ticket List */}
      <div className={`${
        selectedTicketId ? 'hidden lg:block' : 'block'
      } lg:col-span-1 space-y-4 overflow-y-auto pr-2`}>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-display font-bold text-white">INBOX</h3>
          <div className="text-xs font-mono text-gray-500">
            {tickets.filter(t => t.status === 'OPEN').length} OPEN
          </div>
        </div>
        {tickets.map(t => (
          <div 
            key={t.id} 
            onClick={() => setSelectedTicketId(t.id)}
            className={`bg-[#0e0e0e] border p-4 transition-colors cursor-pointer group relative ${
              selectedTicketId === t.id 
                ? 'border-pandora-cyan bg-pandora-cyan/5' 
                : 'border-white/10 hover:border-white/30'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] font-mono text-gray-500">{t.id}</span>
              <span className="text-[10px] font-mono text-gray-600">
                {t.date || t.createdAt}
              </span>
            </div>
            <div className="font-bold text-white text-sm mb-1">{t.subject}</div>
            <div className="text-xs text-gray-400">{t.user}</div>
          </div>
        ))}
      </div>

      {/* Chat Area */}
      <div className={`${
        !selectedTicketId ? 'hidden lg:flex' : 'flex'
      } lg:col-span-2 bg-[#0e0e0e] border border-white/10 flex-col h-full relative`}>
        {selectedTicketId ? (
          <>
            <div className="p-4 border-b border-white/10 flex justify-between items-center bg-black/50">
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => setSelectedTicketId(null)} 
                  className="lg:hidden text-gray-500"
                >
                  <ArrowUpRight className="rotate-[-135deg]" size={20}/>
                </button>
                <h3 className="font-bold text-white">
                  TCK-{selectedTicketId.split('-')[1] || selectedTicketId}
                </h3>
              </div>
              <button className="text-green-500 text-[10px] border border-green-500/30 px-3 py-1">
                RESOLVE
              </button>
            </div>
            <div className="flex-1 p-4 overflow-y-auto">
              <div className="text-center text-gray-600 text-xs mt-10">
                End of encryption history
              </div>
            </div>
            <div className="p-4 border-t border-white/10">
              <input 
                placeholder="Type response..." 
                className="w-full bg-black border border-white/20 p-3 text-xs text-white outline-none" 
              />
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 opacity-50">
            <MessageSquare size={48} className="mb-4" />
            <span className="font-mono text-xs uppercase tracking-widest">Select Ticket</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(AdminSupport);




