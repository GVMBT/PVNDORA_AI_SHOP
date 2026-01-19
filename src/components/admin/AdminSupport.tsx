/**
 * AdminSupport Component
 *
 * Support tickets management view.
 */

import { ArrowUpRight, Check, ExternalLink, MessageSquare, X } from "lucide-react";
import type React from "react";
import { memo, useCallback, useState } from "react";
import { useAdmin } from "../../hooks/useAdmin";
import { logger } from "../../utils/logger";
import type { TicketData } from "./types";

interface AdminSupportProps {
  tickets: TicketData[];
  onRefresh?: () => void;
}

const AdminSupport: React.FC<AdminSupportProps> = ({ tickets, onRefresh }) => {
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [processing, setProcessing] = useState(false);
  const { resolveTicket } = useAdmin();

  const selectedTicket = tickets.find((t) => t.id === selectedTicketId);

  const handleResolve = useCallback(
    async (approve: boolean) => {
      if (!selectedTicketId) {
        return;
      }

      setProcessing(true);
      try {
        // Resolve ticket with comment
        await resolveTicket(selectedTicketId, approve, comment.trim() || undefined);

        setComment("");
        if (onRefresh) {
          onRefresh();
        }
        // Keep ticket selected to see updated status
      } catch (err) {
        logger.error("Failed to resolve ticket", err);
      } finally {
        setProcessing(false);
      }
    },
    [selectedTicketId, comment, resolveTicket, onRefresh]
  );

  const getStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case "OPEN":
        return "text-yellow-400";
      case "APPROVED":
        return "text-green-400";
      case "REJECTED":
        return "text-red-400";
      case "CLOSED":
        return "text-gray-400";
      default:
        return "text-gray-400";
    }
  };

  const getIssueTypeLabel = (issueType?: string) => {
    switch (issueType) {
      case "replacement":
        return "REPLACEMENT";
      case "refund":
        return "REFUND";
      case "technical_issue":
        return "TECHNICAL";
      default:
        return "GENERAL";
    }
  };

  return (
    <div className="grid h-[calc(100vh-200px)] grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Ticket List */}
      <div
        className={`${
          selectedTicketId ? "hidden lg:block" : "block"
        } space-y-4 overflow-y-auto pr-2 lg:col-span-1`}
      >
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-bold font-display text-white">INBOX</h3>
          <div className="font-mono text-gray-500 text-xs">
            {tickets.filter((t) => t.status?.toUpperCase() === "OPEN").length} OPEN
          </div>
        </div>
        {tickets.map((t) => (
          <button
            className={`group relative w-full cursor-pointer border bg-[#0e0e0e] p-4 text-left transition-colors ${
              selectedTicketId === t.id
                ? "border-pandora-cyan bg-pandora-cyan/5"
                : "border-white/10 hover:border-white/30"
            }`}
            key={t.id}
            onClick={() => setSelectedTicketId(t.id)}
            type="button"
          >
            <div className="mb-2 flex items-start justify-between">
              <span className="font-mono text-[10px] text-gray-500">{t.id.slice(0, 8)}</span>
              <span className={`font-mono text-[10px] ${getStatusColor(t.status)}`}>
                {t.status?.toUpperCase() || "OPEN"}
              </span>
            </div>
            <div className="mb-1 font-bold text-sm text-white">
              {t.issue_type ? `[${getIssueTypeLabel(t.issue_type)}] ` : ""}
              {t.subject || t.description?.slice(0, 50) || "No subject"}
            </div>
            <div className="mb-1 text-gray-400 text-xs">{t.user || "Unknown"}</div>
            {t.item_id && (
              <div className="mt-1 font-mono text-[10px] text-gray-500">
                Item: {t.item_id.slice(0, 8)}...
              </div>
            )}
            <div className="mt-1 font-mono text-[10px] text-gray-600">{t.date || t.createdAt}</div>
          </button>
        ))}
      </div>

      {/* Chat Area */}
      <div
        className={`${
          selectedTicketId ? "flex" : "hidden lg:flex"
        } relative h-full flex-col border border-white/10 bg-[#0e0e0e] lg:col-span-2`}
      >
        {selectedTicket ? (
          <>
            <div className="border-white/10 border-b bg-black/50 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button
                    className="text-gray-500 hover:text-white lg:hidden"
                    onClick={() => setSelectedTicketId(null)}
                    type="button"
                  >
                    <ArrowUpRight className="rotate-[-135deg]" size={20} />
                  </button>
                  <div>
                    <h3 className="font-bold text-white">TCK-{selectedTicket.id.slice(0, 8)}</h3>
                    <div className="mt-1 font-mono text-[10px] text-gray-500">
                      {selectedTicket.createdAt || selectedTicket.date}
                    </div>
                  </div>
                </div>
                <div
                  className={`border px-2 py-1 font-mono text-[10px] ${getStatusColor(selectedTicket.status)} border-current/30`}
                >
                  {selectedTicket.status?.toUpperCase() || "OPEN"}
                </div>
              </div>

              {/* Ticket Info */}
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <div className="mb-1 text-gray-500">User</div>
                  <div className="font-mono text-white">{selectedTicket.user || "Unknown"}</div>
                  {selectedTicket.telegram_id && (
                    <a
                      className="mt-1 flex items-center gap-1 text-pandora-cyan hover:text-pandora-cyan/80"
                      href={`tg://user?id=${selectedTicket.telegram_id}`}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      <ExternalLink size={12} />
                      <span>Contact in Telegram</span>
                    </a>
                  )}
                </div>
                <div>
                  <div className="mb-1 text-gray-500">Issue Type</div>
                  <div className="font-mono text-white">
                    {getIssueTypeLabel(selectedTicket.issue_type)}
                  </div>
                </div>
                {selectedTicket.item_id && (
                  <div>
                    <div className="mb-1 text-gray-500">Item ID</div>
                    <div className="font-mono text-[10px] text-white">{selectedTicket.item_id}</div>
                  </div>
                )}
                {selectedTicket.order_id && (
                  <div>
                    <div className="mb-1 text-gray-500">Order ID</div>
                    <div className="font-mono text-[10px] text-white">
                      {selectedTicket.order_id}
                    </div>
                  </div>
                )}
              </div>

              {/* Credentials for Admin Verification */}
              {selectedTicket.credentials && (
                <div className="mt-4 rounded border border-yellow-500/30 bg-yellow-500/10 p-3">
                  <div className="mb-2 font-mono text-[10px] text-yellow-400">
                    ⚠️ CREDENTIALS FOR VERIFICATION
                  </div>
                  {selectedTicket.product_name && (
                    <div className="mb-1 text-gray-400 text-xs">
                      Product: {selectedTicket.product_name}
                    </div>
                  )}
                  <div className="select-all break-all bg-black/50 p-2 font-mono text-sm text-white">
                    {selectedTicket.credentials}
                  </div>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {/* Issue Description */}
              <div className="mb-6">
                <div className="mb-2 font-mono text-[10px] text-gray-500">ISSUE DESCRIPTION</div>
                <div className="whitespace-pre-wrap border border-white/10 bg-black/50 p-4 text-gray-300 text-xs">
                  {selectedTicket.description ||
                    selectedTicket.lastMessage ||
                    "No description provided"}
                </div>
              </div>

              {/* Admin Comment (if exists) */}
              {selectedTicket.admin_comment && (
                <div className="mb-6">
                  <div className="mb-2 font-mono text-[10px] text-gray-500">ADMIN COMMENT</div>
                  <div className="whitespace-pre-wrap border border-pandora-cyan/30 bg-pandora-cyan/10 p-4 text-gray-300 text-xs">
                    {selectedTicket.admin_comment}
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            {selectedTicket.status?.toUpperCase() === "OPEN" ? (
              <div className="space-y-3 border-white/10 border-t p-4">
                <textarea
                  className="w-full resize-none border border-white/20 bg-black p-3 text-white text-xs outline-none"
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add comment (optional)..."
                  rows={3}
                  value={comment}
                />
                <div className="flex gap-2">
                  <button
                    className="flex flex-1 items-center justify-center gap-2 border border-green-500/50 bg-green-500/20 px-4 py-2 font-bold font-mono text-[10px] text-green-400 hover:bg-green-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={processing}
                    onClick={() => handleResolve(true)}
                    type="button"
                  >
                    <Check size={14} />
                    APPROVE
                  </button>
                  <button
                    className="flex flex-1 items-center justify-center gap-2 border border-red-500/50 bg-red-500/20 px-4 py-2 font-bold font-mono text-[10px] text-red-400 hover:bg-red-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={processing}
                    onClick={() => handleResolve(false)}
                    type="button"
                  >
                    <X size={14} />
                    REJECT
                  </button>
                </div>
              </div>
            ) : (
              <div className="border-white/10 border-t p-4">
                <div className="text-center text-gray-600 text-xs">
                  Ticket is {selectedTicket.status?.toUpperCase()}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center text-gray-600 opacity-50">
            <MessageSquare className="mb-4" size={48} />
            <span className="font-mono text-xs uppercase tracking-widest">Select Ticket</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(AdminSupport);
