/**
 * AdminPartners Component
 *
 * Управление VIP партнёрами и заявками.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  Calendar,
  Check,
  Crown,
  Edit,
  ExternalLink,
  RefreshCw,
  User,
  Users,
  X,
} from "lucide-react";
import type React from "react";
import { memo, useCallback, useEffect, useState } from "react";
import { API } from "../../config";
import { apiRequest } from "../../utils/apiClient";
import { logger } from "../../utils/logger";
import StatusBadge from "./StatusBadge";
import type { UserData } from "./types";

// Partner Application type
interface PartnerApplication {
  id: string;
  user_id: string;
  telegram_id?: number;
  username?: string;
  first_name?: string;
  motivation?: string;
  channels_description?: string;
  expected_referrals?: number;
  status: "pending" | "approved" | "rejected";
  admin_comment?: string;
  created_at: string;
  reviewed_at?: string;
}

interface AdminPartnersProps {
  partners: UserData[];
  onEditPartner: (partner: UserData) => void;
  onRevokeVIP?: (partner: UserData) => Promise<void>;
  onRefresh?: () => void;
}

type PartnerTab = "list" | "requests";

// Helper: Format date for Russian locale
const formatDateRu = (dateStr: string): string => {
  return new Date(dateStr).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// Helper: Status badge configuration
const STATUS_BADGE_CONFIG: Record<string, { text: string; colorClass: string } | undefined> = {
  pending: { text: "Ожидает", colorClass: "text-yellow-500 bg-yellow-500/10 border-yellow-500/30" },
  approved: { text: "Одобрено", colorClass: "text-green-500 bg-green-500/10 border-green-500/30" },
  rejected: { text: "Отклонено", colorClass: "text-red-500 bg-red-500/10 border-red-500/30" },
};

const getStatusBadge = (status: string): React.ReactNode => {
  const config = STATUS_BADGE_CONFIG[status];
  if (!config) return null;
  return (
    <span className={`${config.colorClass} border px-2 py-0.5 text-[10px] uppercase`}>
      {config.text}
    </span>
  );
};

// Helper function to render applications grid content
const renderApplicationsContent = (
  loadingApplications: boolean,
  applications: PartnerApplication[],
  filter: "pending" | "all",
  setSelectedApp: (app: PartnerApplication) => void
): React.ReactNode => {
  if (loadingApplications) {
    return (
      <div className="text-center py-8">
        <RefreshCw size={24} className="animate-spin text-pandora-cyan mx-auto" />
      </div>
    );
  }

  if (applications.length === 0) {
    return (
      <div className="text-center text-gray-600 text-xs py-8 bg-white/5 border border-white/10">
        {filter === "pending" ? "Нет ожидающих заявок" : "Заявки не найдены"}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {applications.map((app) => (
        <motion.div
          key={app.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`bg-[#0e0e0e] border p-4 cursor-pointer transition-colors ${
            app.status === "pending"
              ? "border-yellow-500/30 hover:border-yellow-500"
              : "border-white/10 hover:border-white/30"
          }`}
          onClick={() => setSelectedApp(app)}
        >
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center gap-2">
              <User size={14} className="text-gray-500" />
              <span className="font-bold text-white">
                {app.first_name || app.username || "Пользователь"}
              </span>
            </div>
            {getStatusBadge(app.status)}
          </div>

          <div className="text-xs text-gray-500 mb-2 flex items-center gap-2">
            <Calendar size={12} />
            {formatDateRu(app.created_at)}
          </div>

          {Boolean(app.motivation) && (
            <p className="text-xs text-gray-400 line-clamp-2 mb-2">{app.motivation}</p>
          )}

          {app.expected_referrals != null && app.expected_referrals > 0 && (
            <div className="text-[10px] text-gray-500">
              Ожидаемые рефералы: {app.expected_referrals}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
};

const AdminPartners: React.FC<AdminPartnersProps> = ({
  partners,
  onEditPartner,
  onRevokeVIP,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<PartnerTab>("list");
  const [applications, setApplications] = useState<PartnerApplication[]>([]);
  const [loadingApplications, setLoadingApplications] = useState(false);
  const [selectedApp, setSelectedApp] = useState<PartnerApplication | null>(null);
  const [reviewComment, setReviewComment] = useState("");
  const [processing, setProcessing] = useState(false);
  const [filter, setFilter] = useState<"pending" | "all">("pending");

  // Fetch applications
  const fetchApplications = useCallback(async () => {
    setLoadingApplications(true);
    try {
      const response = await apiRequest<{ applications: PartnerApplication[] }>(
        `${API.ADMIN_URL}/partner-applications?status=${filter}`
      );
      setApplications(response.applications || []);
    } catch (err) {
      logger.error("Failed to fetch partner applications", err);
    } finally {
      setLoadingApplications(false);
    }
  }, [filter]);

  useEffect(() => {
    if (activeTab === "requests") {
      fetchApplications();
    }
  }, [activeTab, fetchApplications]);

  // Review application (approve/reject)
  const handleReview = async (approve: boolean) => {
    if (!selectedApp) return;
    setProcessing(true);

    try {
      await apiRequest(`${API.ADMIN_URL}/partner-applications/review`, {
        method: "POST",
        body: JSON.stringify({
          application_id: selectedApp.id,
          approve,
          admin_comment: reviewComment || null,
          level_override: approve ? 3 : null, // VIP always gets level 3 (full access)
        }),
      });

      // Refresh and close
      await fetchApplications();
      setSelectedApp(null);
      setReviewComment("");
      if (onRefresh) onRefresh();
    } catch (err) {
      logger.error("Failed to review application", err);
      globalThis.alert("Ошибка при обработке заявки");
    } finally {
      setProcessing(false);
    }
  };

  const pendingCount = applications.filter((a) => a.status === "pending").length;

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-4 border-b border-white/10 pb-1 overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab("list")}
          className={`text-xs font-bold uppercase pb-2 px-2 transition-colors flex items-center gap-2 ${
            activeTab === "list"
              ? "text-pandora-cyan border-b-2 border-pandora-cyan"
              : "text-gray-500 hover:text-white"
          }`}
        >
          <Crown size={14} />
          VIP Партнёры
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("requests")}
          className={`text-xs font-bold uppercase pb-2 px-2 transition-colors flex items-center gap-2 ${
            activeTab === "requests"
              ? "text-pandora-cyan border-b-2 border-pandora-cyan"
              : "text-gray-500 hover:text-white"
          }`}
        >
          <Users size={14} />
          Заявки
          {pendingCount > 0 && (
            <span className="bg-red-500 text-white px-1.5 rounded-sm text-[9px] font-bold">
              {pendingCount}
            </span>
          )}
        </button>
      </div>

      {activeTab === "list" ? (
        <>
          {/* Partners List - Desktop */}
          <div className="bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden hidden md:block">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-white/5 text-gray-400 uppercase">
                <tr>
                  <th className="p-4">Пользователь</th>
                  <th className="p-4">Уровень</th>
                  <th className="p-4">Заработок</th>
                  <th className="p-4">Режим</th>
                  <th className="p-4">Статус</th>
                  <th className="p-4">Действие</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-gray-300">
                {partners.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-gray-600">
                      Нет VIP партнёров
                    </td>
                  </tr>
                ) : (
                  partners.map((p) => (
                    <tr key={p.id} className="hover:bg-white/5 transition-colors">
                      <td className="p-4 font-bold text-white">{p.handle || p.username}</td>
                      <td className="p-4">
                        <span
                          className={`text-[10px] px-2 py-0.5 border ${
                            p.level === "ARCHITECT"
                              ? "border-yellow-500 text-yellow-500"
                              : "border-gray-500 text-gray-500"
                          }`}
                        >
                          {p.level || "USER"}
                        </span>
                      </td>
                      <td className="p-4 text-pandora-cyan">{p.earned || 0} USD</td>
                      <td className="p-4 text-[10px] uppercase text-gray-400">
                        {p.rewardType === "commission" ? "💰 Комиссия" : "🎁 Скидка рефералам"}
                      </td>
                      <td className="p-4">
                        <StatusBadge status={p.status || "ACTIVE"} />
                      </td>
                      <td className="p-4 flex gap-2">
                        <button
                          type="button"
                          onClick={() => onEditPartner(p)}
                          className="hover:text-pandora-cyan transition-colors"
                          title="Редактировать"
                        >
                          <Edit size={14} />
                        </button>
                        {onRevokeVIP && (
                          <button
                            type="button"
                            onClick={async () => {
                              if (confirm(`Отозвать VIP статус у ${p.username}?`)) {
                                await onRevokeVIP(p);
                              }
                            }}
                            className="hover:text-red-500 transition-colors text-gray-500"
                            title="Отозвать VIP"
                          >
                            <X size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Partners */}
          <div className="md:hidden space-y-4">
            {partners.length === 0 ? (
              <div className="text-center text-gray-600 text-xs py-8">Нет VIP партнёров</div>
            ) : (
              partners.map((p) => (
                <div key={p.id} className="bg-[#0e0e0e] border border-white/10 p-4 relative">
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-bold text-white">{p.handle || p.username}</span>
                    <StatusBadge status={p.status || "ACTIVE"} />
                  </div>
                  <div className="text-xs text-gray-500 mb-2">
                    {p.level || "USER"} • Заработок: {p.earned || 0} USD
                  </div>
                  <button
                    type="button"
                    onClick={() => onEditPartner(p)}
                    className="w-full text-[10px] bg-white/5 py-2 hover:bg-pandora-cyan hover:text-black transition-colors uppercase font-bold"
                  >
                    Управление
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      ) : (
        <div className="space-y-4">
          {/* Filter & Refresh */}
          <div className="flex justify-between items-center">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setFilter("pending")}
                className={`px-3 py-1.5 text-[10px] font-bold uppercase transition-colors ${
                  filter === "pending"
                    ? "bg-pandora-cyan text-black"
                    : "bg-white/5 text-gray-400 hover:text-white"
                }`}
              >
                Ожидающие
              </button>
              <button
                type="button"
                onClick={() => setFilter("all")}
                className={`px-3 py-1.5 text-[10px] font-bold uppercase transition-colors ${
                  filter === "all"
                    ? "bg-pandora-cyan text-black"
                    : "bg-white/5 text-gray-400 hover:text-white"
                }`}
              >
                Все
              </button>
            </div>
            <button
              type="button"
              onClick={fetchApplications}
              disabled={loadingApplications}
              className="p-2 text-gray-400 hover:text-pandora-cyan transition-colors disabled:opacity-50"
            >
              <RefreshCw size={16} className={loadingApplications ? "animate-spin" : ""} />
            </button>
          </div>

          {/* Applications Grid */}
          {renderApplicationsContent(loadingApplications, applications, filter, setSelectedApp)}
        </div>
      )}

      {/* Application Review Modal */}
      <AnimatePresence>
        {selectedApp && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <div
              role="button"
              tabIndex={0}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
              onClick={() => !processing && setSelectedApp(null)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && !processing) setSelectedApp(null);
              }}
            />
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-lg bg-[#080808] border border-white/20 p-6 shadow-2xl"
            >
              {/* Header */}
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <Crown size={18} className="text-yellow-500" />
                    Заявка на VIP
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">ID: {selectedApp.id.slice(0, 8)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => !processing && setSelectedApp(null)}
                  className="text-gray-500 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Applicant Info */}
              <div className="space-y-4 mb-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-black/50 p-3 border border-white/10">
                    <div className="text-[10px] text-gray-500 uppercase mb-1">Пользователь</div>
                    <div className="text-white font-bold">
                      {selectedApp.first_name || selectedApp.username || "Неизвестно"}
                    </div>
                  </div>
                  <div className="bg-black/50 p-3 border border-white/10">
                    <div className="text-[10px] text-gray-500 uppercase mb-1">Telegram ID</div>
                    <div className="text-white font-mono">
                      {selectedApp.telegram_id || "N/A"}
                      {selectedApp.telegram_id && (
                        <a
                          href={`tg://user?id=${selectedApp.telegram_id}`}
                          className="ml-2 text-pandora-cyan hover:underline"
                        >
                          <ExternalLink size={12} className="inline" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>

                <div className="bg-black/50 p-3 border border-white/10">
                  <div className="text-[10px] text-gray-500 uppercase mb-1">Дата подачи</div>
                  <div className="text-white">{formatDateRu(selectedApp.created_at)}</div>
                </div>

                {selectedApp.motivation && (
                  <div className="bg-black/50 p-3 border border-white/10">
                    <div className="text-[10px] text-gray-500 uppercase mb-1">Мотивация</div>
                    <p className="text-gray-300 text-sm">{selectedApp.motivation}</p>
                  </div>
                )}

                {selectedApp.channels_description && (
                  <div className="bg-black/50 p-3 border border-white/10">
                    <div className="text-[10px] text-gray-500 uppercase mb-1">Описание каналов</div>
                    <p className="text-gray-300 text-sm">{selectedApp.channels_description}</p>
                  </div>
                )}

                {selectedApp.expected_referrals && (
                  <div className="bg-black/50 p-3 border border-white/10">
                    <div className="text-[10px] text-gray-500 uppercase mb-1">
                      Ожидаемые рефералы
                    </div>
                    <div className="text-pandora-cyan font-bold">
                      {selectedApp.expected_referrals}
                    </div>
                  </div>
                )}
              </div>

              {/* Review Section - only for pending */}
              {selectedApp.status === "pending" ? (
                <div className="space-y-4">
                  {/* VIP Info */}
                  <div className="bg-yellow-500/10 border border-yellow-500/30 p-3 text-xs text-yellow-400">
                    <p className="font-bold mb-1">При одобрении пользователь получит:</p>
                    <ul className="list-disc list-inside text-yellow-400/80 space-y-1">
                      <li>Статус VIP / ARCHITECT</li>
                      <li>Все реферальные уровни открыты</li>
                      <li>Максимальные комиссии</li>
                    </ul>
                  </div>

                  {/* Comment */}
                  <div>
                    <label
                      htmlFor="review-comment"
                      className="text-[10px] text-gray-500 uppercase mb-1 block"
                    >
                      Комментарий (опционально)
                    </label>
                    <textarea
                      id="review-comment"
                      value={reviewComment}
                      onChange={(e) => setReviewComment(e.target.value)}
                      placeholder="Комментарий для пользователя..."
                      className="w-full h-20 bg-black border border-white/20 p-2 text-white text-sm focus:border-pandora-cyan outline-none resize-none"
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => handleReview(true)}
                      disabled={processing}
                      className="flex-1 py-2.5 bg-green-500 text-black font-bold text-sm hover:bg-green-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      <Check size={16} />
                      Одобрить
                    </button>
                    <button
                      type="button"
                      onClick={() => handleReview(false)}
                      disabled={processing}
                      className="flex-1 py-2.5 bg-red-500 text-white font-bold text-sm hover:bg-red-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      <X size={16} />
                      Отклонить
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-white/5 p-4 border border-white/10">
                  <div className="flex items-center gap-2 mb-2">
                    {getStatusBadge(selectedApp.status)}
                    {selectedApp.reviewed_at && (
                      <span className="text-xs text-gray-500">
                        {formatDateRu(selectedApp.reviewed_at)}
                      </span>
                    )}
                  </div>
                  {selectedApp.admin_comment && (
                    <p className="text-sm text-gray-400">{selectedApp.admin_comment}</p>
                  )}
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default memo(AdminPartners);
