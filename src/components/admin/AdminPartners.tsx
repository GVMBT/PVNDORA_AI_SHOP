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
      <div className="py-8 text-center">
        <RefreshCw className="mx-auto animate-spin text-pandora-cyan" size={24} />
      </div>
    );
  }

  if (applications.length === 0) {
    return (
      <div className="border border-white/10 bg-white/5 py-8 text-center text-gray-600 text-xs">
        {filter === "pending" ? "Нет ожидающих заявок" : "Заявки не найдены"}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {applications.map((app) => (
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className={`cursor-pointer border bg-[#0e0e0e] p-4 transition-colors ${
            app.status === "pending"
              ? "border-yellow-500/30 hover:border-yellow-500"
              : "border-white/10 hover:border-white/30"
          }`}
          initial={{ opacity: 0, y: 10 }}
          key={app.id}
          onClick={() => setSelectedApp(app)}
        >
          <div className="mb-3 flex items-start justify-between">
            <div className="flex items-center gap-2">
              <User className="text-gray-500" size={14} />
              <span className="font-bold text-white">
                {app.first_name || app.username || "Пользователь"}
              </span>
            </div>
            {getStatusBadge(app.status)}
          </div>

          <div className="mb-2 flex items-center gap-2 text-gray-500 text-xs">
            <Calendar size={12} />
            {formatDateRu(app.created_at)}
          </div>

          {Boolean(app.motivation) && (
            <p className="mb-2 line-clamp-2 text-gray-400 text-xs">{app.motivation}</p>
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
      <div className="flex gap-4 overflow-x-auto border-white/10 border-b pb-1">
        <button
          className={`flex items-center gap-2 px-2 pb-2 font-bold text-xs uppercase transition-colors ${
            activeTab === "list"
              ? "border-pandora-cyan border-b-2 text-pandora-cyan"
              : "text-gray-500 hover:text-white"
          }`}
          onClick={() => setActiveTab("list")}
          type="button"
        >
          <Crown size={14} />
          VIP Партнёры
        </button>
        <button
          className={`flex items-center gap-2 px-2 pb-2 font-bold text-xs uppercase transition-colors ${
            activeTab === "requests"
              ? "border-pandora-cyan border-b-2 text-pandora-cyan"
              : "text-gray-500 hover:text-white"
          }`}
          onClick={() => setActiveTab("requests")}
          type="button"
        >
          <Users size={14} />
          Заявки
          {pendingCount > 0 && (
            <span className="rounded-sm bg-red-500 px-1.5 font-bold text-[9px] text-white">
              {pendingCount}
            </span>
          )}
        </button>
      </div>

      {activeTab === "list" ? (
        <>
          {/* Partners List - Desktop */}
          <div className="hidden overflow-hidden rounded-sm border border-white/10 bg-[#0e0e0e] md:block">
            <table className="w-full text-left font-mono text-xs">
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
                    <td className="p-8 text-center text-gray-600" colSpan={6}>
                      Нет VIP партнёров
                    </td>
                  </tr>
                ) : (
                  partners.map((p) => (
                    <tr className="transition-colors hover:bg-white/5" key={p.id}>
                      <td className="p-4 font-bold text-white">{p.handle || p.username}</td>
                      <td className="p-4">
                        <span
                          className={`border px-2 py-0.5 text-[10px] ${
                            p.level === "ARCHITECT"
                              ? "border-yellow-500 text-yellow-500"
                              : "border-gray-500 text-gray-500"
                          }`}
                        >
                          {p.level || "USER"}
                        </span>
                      </td>
                      <td className="p-4 text-pandora-cyan">{p.earned || 0} ₽</td>
                      <td className="p-4 text-[10px] text-gray-400 uppercase">
                        {p.rewardType === "commission" ? "💰 Комиссия" : "🎁 Скидка рефералам"}
                      </td>
                      <td className="p-4">
                        <StatusBadge status={p.status || "ACTIVE"} />
                      </td>
                      <td className="flex gap-2 p-4">
                        <button
                          className="transition-colors hover:text-pandora-cyan"
                          onClick={() => onEditPartner(p)}
                          title="Редактировать"
                          type="button"
                        >
                          <Edit size={14} />
                        </button>
                        {onRevokeVIP && (
                          <button
                            className="text-gray-500 transition-colors hover:text-red-500"
                            onClick={async () => {
                              if (confirm(`Отозвать VIP статус у ${p.username}?`)) {
                                await onRevokeVIP(p);
                              }
                            }}
                            title="Отозвать VIP"
                            type="button"
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
          <div className="space-y-4 md:hidden">
            {partners.length === 0 ? (
              <div className="py-8 text-center text-gray-600 text-xs">Нет VIP партнёров</div>
            ) : (
              partners.map((p) => (
                <div className="relative border border-white/10 bg-[#0e0e0e] p-4" key={p.id}>
                  <div className="mb-2 flex items-start justify-between">
                    <span className="font-bold text-white">{p.handle || p.username}</span>
                    <StatusBadge status={p.status || "ACTIVE"} />
                  </div>
                  <div className="mb-2 text-gray-500 text-xs">
                    {p.level || "USER"} • Заработок: {p.earned || 0} ₽
                  </div>
                  <button
                    className="w-full bg-white/5 py-2 font-bold text-[10px] uppercase transition-colors hover:bg-pandora-cyan hover:text-black"
                    onClick={() => onEditPartner(p)}
                    type="button"
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
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <button
                className={`px-3 py-1.5 font-bold text-[10px] uppercase transition-colors ${
                  filter === "pending"
                    ? "bg-pandora-cyan text-black"
                    : "bg-white/5 text-gray-400 hover:text-white"
                }`}
                onClick={() => setFilter("pending")}
                type="button"
              >
                Ожидающие
              </button>
              <button
                className={`px-3 py-1.5 font-bold text-[10px] uppercase transition-colors ${
                  filter === "all"
                    ? "bg-pandora-cyan text-black"
                    : "bg-white/5 text-gray-400 hover:text-white"
                }`}
                onClick={() => setFilter("all")}
                type="button"
              >
                Все
              </button>
            </div>
            <button
              className="p-2 text-gray-400 transition-colors hover:text-pandora-cyan disabled:opacity-50"
              disabled={loadingApplications}
              onClick={fetchApplications}
              type="button"
            >
              <RefreshCw className={loadingApplications ? "animate-spin" : ""} size={16} />
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
            <button
              aria-label="Close modal"
              className="absolute inset-0 cursor-default bg-black/80 backdrop-blur-sm"
              onClick={() => !processing && setSelectedApp(null)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && !processing) setSelectedApp(null);
              }}
              type="button"
            />
            <motion.div
              animate={{ scale: 1, opacity: 1 }}
              className="relative w-full max-w-lg border border-white/20 bg-[#080808] p-6 shadow-2xl"
              exit={{ scale: 0.9, opacity: 0 }}
              initial={{ scale: 0.9, opacity: 0 }}
            >
              {/* Header */}
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <h3 className="flex items-center gap-2 font-bold text-lg text-white">
                    <Crown className="text-yellow-500" size={18} />
                    Заявка на VIP
                  </h3>
                  <p className="mt-1 text-gray-500 text-xs">ID: {selectedApp.id.slice(0, 8)}</p>
                </div>
                <button
                  className="text-gray-500 hover:text-white"
                  onClick={() => !processing && setSelectedApp(null)}
                  type="button"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Applicant Info */}
              <div className="mb-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="border border-white/10 bg-black/50 p-3">
                    <div className="mb-1 text-[10px] text-gray-500 uppercase">Пользователь</div>
                    <div className="font-bold text-white">
                      {selectedApp.first_name || selectedApp.username || "Неизвестно"}
                    </div>
                  </div>
                  <div className="border border-white/10 bg-black/50 p-3">
                    <div className="mb-1 text-[10px] text-gray-500 uppercase">Telegram ID</div>
                    <div className="font-mono text-white">
                      {selectedApp.telegram_id || "N/A"}
                      {selectedApp.telegram_id && (
                        <a
                          className="ml-2 text-pandora-cyan hover:underline"
                          href={`tg://user?id=${selectedApp.telegram_id}`}
                        >
                          <ExternalLink className="inline" size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                </div>

                <div className="border border-white/10 bg-black/50 p-3">
                  <div className="mb-1 text-[10px] text-gray-500 uppercase">Дата подачи</div>
                  <div className="text-white">{formatDateRu(selectedApp.created_at)}</div>
                </div>

                {selectedApp.motivation && (
                  <div className="border border-white/10 bg-black/50 p-3">
                    <div className="mb-1 text-[10px] text-gray-500 uppercase">Мотивация</div>
                    <p className="text-gray-300 text-sm">{selectedApp.motivation}</p>
                  </div>
                )}

                {selectedApp.channels_description && (
                  <div className="border border-white/10 bg-black/50 p-3">
                    <div className="mb-1 text-[10px] text-gray-500 uppercase">Описание каналов</div>
                    <p className="text-gray-300 text-sm">{selectedApp.channels_description}</p>
                  </div>
                )}

                {selectedApp.expected_referrals && (
                  <div className="border border-white/10 bg-black/50 p-3">
                    <div className="mb-1 text-[10px] text-gray-500 uppercase">
                      Ожидаемые рефералы
                    </div>
                    <div className="font-bold text-pandora-cyan">
                      {selectedApp.expected_referrals}
                    </div>
                  </div>
                )}
              </div>

              {/* Review Section - only for pending */}
              {selectedApp.status === "pending" ? (
                <div className="space-y-4">
                  {/* VIP Info */}
                  <div className="border border-yellow-500/30 bg-yellow-500/10 p-3 text-xs text-yellow-400">
                    <p className="mb-1 font-bold">При одобрении пользователь получит:</p>
                    <ul className="list-inside list-disc space-y-1 text-yellow-400/80">
                      <li>Статус VIP / ARCHITECT</li>
                      <li>Все реферальные уровни открыты</li>
                      <li>Максимальные комиссии</li>
                    </ul>
                  </div>

                  {/* Comment */}
                  <div>
                    <label
                      className="mb-1 block text-[10px] text-gray-500 uppercase"
                      htmlFor="review-comment"
                    >
                      Комментарий (опционально)
                    </label>
                    <textarea
                      className="h-20 w-full resize-none border border-white/20 bg-black p-2 text-sm text-white outline-none focus:border-pandora-cyan"
                      id="review-comment"
                      onChange={(e) => setReviewComment(e.target.value)}
                      placeholder="Комментарий для пользователя..."
                      value={reviewComment}
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 pt-2">
                    <button
                      className="flex flex-1 items-center justify-center gap-2 bg-green-500 py-2.5 font-bold text-black text-sm transition-colors hover:bg-green-400 disabled:opacity-50"
                      disabled={processing}
                      onClick={() => handleReview(true)}
                      type="button"
                    >
                      <Check size={16} />
                      Одобрить
                    </button>
                    <button
                      className="flex flex-1 items-center justify-center gap-2 bg-red-500 py-2.5 font-bold text-sm text-white transition-colors hover:bg-red-400 disabled:opacity-50"
                      disabled={processing}
                      onClick={() => handleReview(false)}
                      type="button"
                    >
                      <X size={16} />
                      Отклонить
                    </button>
                  </div>
                </div>
              ) : (
                <div className="border border-white/10 bg-white/5 p-4">
                  <div className="mb-2 flex items-center gap-2">
                    {getStatusBadge(selectedApp.status)}
                    {selectedApp.reviewed_at && (
                      <span className="text-gray-500 text-xs">
                        {formatDateRu(selectedApp.reviewed_at)}
                      </span>
                    )}
                  </div>
                  {selectedApp.admin_comment && (
                    <p className="text-gray-400 text-sm">{selectedApp.admin_comment}</p>
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
