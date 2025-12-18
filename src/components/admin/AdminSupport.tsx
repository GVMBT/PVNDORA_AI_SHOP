/**
 * AdminSupport Component
 * 
 * Support tickets management view.
 */

import React, { useState, memo, useCallback } from 'react';
import { MessageSquare, ArrowUpRight, Check, X, Send, ExternalLink } from 'lucide-react';
import type { TicketData } from './types';
import { useAdmin } from '../../hooks/useAdmin';
import { logger } from '../../utils/logger';

interface AdminSupportProps {
  tickets: TicketData[];
  onRefresh?: () => void;
}

const AdminSupport: React.FC<AdminSupportProps> = ({ tickets, onRefresh }) => {
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [comment, setComment] = useState('');
  const [processing, setProcessing] = useState(false);
  const { resolveTicket } = useAdmin();

  const selectedTicket = tickets.find(t => t.id === selectedTicketId);

  const handleResolve = useCallback(async (approve: boolean) => {
    if (!selectedTicketId) return;
    
    setProcessing(true);
    try {
      // Resolve ticket with comment
      await resolveTicket(selectedTicketId, approve, comment.trim() || undefined);
      
      setComment('');
      if (onRefresh) {
        onRefresh();
      }
      // Keep ticket selected to see updated status
    } catch (err) {
      logger.error('Failed to resolve ticket', err);
    } finally {
      setProcessing(false);
    }
  }, [selectedTicketId, comment, resolveTicket, onRefresh]);

  const getStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'OPEN': return 'text-yellow-400';
      case 'APPROVED': return 'text-green-400';
      case 'REJECTED': return 'text-red-400';
      case 'CLOSED': return 'text-gray-400';
      default: return 'text-gray-400';
    }
  };

  const getIssueTypeLabel = (issueType?: string) => {
    switch (issueType) {
      case 'replacement': return 'REPLACEMENT';
      case 'refund': return 'REFUND';
      case 'technical_issue': return 'TECHNICAL';
      default: return 'GENERAL';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
      {/* Ticket List */}
      <div className={`${
        selectedTicketId ? 'hidden lg:block' : 'block'
      } lg:col-span-1 space-y-4 overflow-y-auto pr-2`}>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-display font-bold text-white">INBOX</h3>
          <div className="text-xs font-mono text-gray-500">
            {tickets.filter(t => t.status === 'OPEN' || t.status === 'open').length} OPEN
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
              <span className="text-[10px] font-mono text-gray-500">{t.id.slice(0, 8)}</span>
              <span className={`text-[10px] font-mono ${getStatusColor(t.status)}`}>
                {t.status?.toUpperCase() || 'OPEN'}
              </span>
            </div>
            <div className="font-bold text-white text-sm mb-1">
              {t.issue_type ? `[${getIssueTypeLabel(t.issue_type)}] ` : ''}
              {t.subject || t.description?.slice(0, 50) || 'No subject'}
            </div>
            <div className="text-xs text-gray-400 mb-1">{t.user || 'Unknown'}</div>
            {t.item_id && (
              <div className="text-[10px] font-mono text-gray-500 mt-1">
                Item: {t.item_id.slice(0, 8)}...
              </div>
            )}
            <div className="text-[10px] font-mono text-gray-600 mt-1">
              {t.date || t.createdAt}
            </div>
          </div>
        ))}
      </div>

      {/* Chat Area */}
      <div className={`${
        !selectedTicketId ? 'hidden lg:flex' : 'flex'
      } lg:col-span-2 bg-[#0e0e0e] border border-white/10 flex-col h-full relative`}>
        {selectedTicket ? (
          <>
            <div className="p-4 border-b border-white/10 bg-black/50">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => setSelectedTicketId(null)} 
                    className="lg:hidden text-gray-500 hover:text-white"
                  >
                    <ArrowUpRight className="rotate-[-135deg]" size={20}/>
                  </button>
                  <div>
                    <h3 className="font-bold text-white">
                      TCK-{selectedTicket.id.slice(0, 8)}
                    </h3>
                    <div className="text-[10px] font-mono text-gray-500 mt-1">
                      {selectedTicket.createdAt || selectedTicket.date}
                    </div>
                  </div>
                </div>
                <div className={`text-[10px] font-mono px-2 py-1 border ${getStatusColor(selectedTicket.status)} border-current/30`}>
                  {selectedTicket.status?.toUpperCase() || 'OPEN'}
                </div>
              </div>
              
              {/* Ticket Info */}
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <div className="text-gray-500 mb-1">User</div>
                  <div className="text-white font-mono">{selectedTicket.user || 'Unknown'}</div>
                  {selectedTicket.telegram_id && (
                    <a
                      href={`tg://user?id=${selectedTicket.telegram_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-pandora-cyan hover:text-pandora-cyan/80 mt-1"
                    >
                      <ExternalLink size={12} />
                      <span>Contact in Telegram</span>
                    </a>
                  )}
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Issue Type</div>
                  <div className="text-white font-mono">{getIssueTypeLabel(selectedTicket.issue_type)}</div>
                </div>
                {selectedTicket.item_id && (
                  <div>
                    <div className="text-gray-500 mb-1">Item ID</div>
                    <div className="text-white font-mono text-[10px]">{selectedTicket.item_id}</div>
                  </div>
                )}
                {selectedTicket.order_id && (
                  <div>
                    <div className="text-gray-500 mb-1">Order ID</div>
                    <div className="text-white font-mono text-[10px]">{selectedTicket.order_id}</div>
                  </div>
                )}
              </div>
              
              {/* Credentials for Admin Verification */}
              {selectedTicket.credentials && (
                <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
                  <div className="text-[10px] font-mono text-yellow-400 mb-2">⚠️ CREDENTIALS FOR VERIFICATION</div>
                  {selectedTicket.product_name && (
                    <div className="text-xs text-gray-400 mb-1">Product: {selectedTicket.product_name}</div>
                  )}
                  <div className="font-mono text-sm text-white bg-black/50 p-2 break-all select-all">
                    {selectedTicket.credentials}
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex-1 p-4 overflow-y-auto">
              {/* Issue Description */}
              <div className="mb-6">
                <div className="text-[10px] font-mono text-gray-500 mb-2">ISSUE DESCRIPTION</div>
                <div className="bg-black/50 border border-white/10 p-4 text-xs text-gray-300 whitespace-pre-wrap">
                  {selectedTicket.description || selectedTicket.lastMessage || 'No description provided'}
                </div>
              </div>
              
              {/* Admin Comment (if exists) */}
              {selectedTicket.admin_comment && (
                <div className="mb-6">
                  <div className="text-[10px] font-mono text-gray-500 mb-2">ADMIN COMMENT</div>
                  <div className="bg-pandora-cyan/10 border border-pandora-cyan/30 p-4 text-xs text-gray-300 whitespace-pre-wrap">
                    {selectedTicket.admin_comment}
                  </div>
                </div>
              )}
            </div>
            
            {/* Action Buttons */}
            {selectedTicket.status === 'OPEN' || selectedTicket.status === 'open' ? (
              <div className="p-4 border-t border-white/10 space-y-3">
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add comment (optional)..."
                  className="w-full bg-black border border-white/20 p-3 text-xs text-white outline-none resize-none"
                  rows={3}
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleResolve(true)}
                    disabled={processing}
                    className="flex-1 flex items-center justify-center gap-2 bg-green-500/20 border border-green-500/50 text-green-400 px-4 py-2 text-[10px] font-bold font-mono hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Check size={14} />
                    APPROVE
                  </button>
                  <button
                    onClick={() => handleResolve(false)}
                    disabled={processing}
                    className="flex-1 flex items-center justify-center gap-2 bg-red-500/20 border border-red-500/50 text-red-400 px-4 py-2 text-[10px] font-bold font-mono hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <X size={14} />
                    REJECT
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-4 border-t border-white/10">
                <div className="text-center text-gray-600 text-xs">
                  Ticket is {selectedTicket.status?.toUpperCase()}
                </div>
              </div>
            )}
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








