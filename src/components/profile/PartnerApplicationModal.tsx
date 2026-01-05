/**
 * Partner Application Modal
 * 
 * Form for users to apply for VIP partnership.
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Loader2, CheckCircle, AlertCircle, Star } from 'lucide-react';

interface PartnerApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: PartnerApplicationData) => Promise<{ success: boolean; message?: string }>;
  existingApplication?: {
    status: string;
    created_at: string;
    admin_comment?: string;
  } | null;
}

export interface PartnerApplicationData {
  email: string;
  phone: string;
  source: string;
  audienceSize: string;
  description: string;
  expectedVolume?: string;
  socialLinks?: Record<string, string>;
}

const AUDIENCE_SOURCES = [
  { value: 'telegram', label: 'Telegram канал/группа' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'twitter', label: 'Twitter/X' },
  { value: 'website', label: 'Веб-сайт/Блог' },
  { value: 'other', label: 'Другое' },
];

const AUDIENCE_SIZES = [
  { value: '1-1000', label: 'До 1,000' },
  { value: '1000-5000', label: '1,000 - 5,000' },
  { value: '5000-10000', label: '5,000 - 10,000' },
  { value: '10000-50000', label: '10,000 - 50,000' },
  { value: '50000+', label: '50,000+' },
];

export const PartnerApplicationModal: React.FC<PartnerApplicationModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  existingApplication,
}) => {
  const [formData, setFormData] = useState<PartnerApplicationData>({
    email: '',
    phone: '',
    source: '',
    audienceSize: '',
    description: '',
    expectedVolume: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = useCallback((field: keyof PartnerApplicationData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.email || !formData.phone || !formData.source || !formData.audienceSize || !formData.description) {
      setError('Заполните все обязательные поля');
      return;
    }
    
    if (!formData.email.includes('@')) {
      setError('Некорректный email');
      return;
    }
    
    setSubmitting(true);
    setError(null);
    
    try {
      const result = await onSubmit(formData);
      if (result.success) {
        setSubmitted(true);
      } else {
        setError(result.message || 'Не удалось отправить заявку');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setSubmitting(false);
    }
  }, [formData, onSubmit]);

  // Show existing application status
  if (existingApplication) {
    const statusInfo = {
      pending: { icon: Loader2, color: 'text-yellow-500', text: 'На рассмотрении' },
      approved: { icon: CheckCircle, color: 'text-green-500', text: 'Одобрена' },
      rejected: { icon: AlertCircle, color: 'text-red-500', text: 'Отклонена' },
    }[existingApplication.status] || { icon: AlertCircle, color: 'text-gray-500', text: existingApplication.status };
    
    const StatusIcon = statusInfo.icon;
    
    return (
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
            onClick={onClose}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#0a0a0a] border border-white/10 rounded-lg p-6 w-full max-w-md"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-white">Статус заявки</h2>
                <button onClick={onClose} className="text-gray-500 hover:text-white">
                  <X size={20} />
                </button>
              </div>
              
              <div className="text-center py-8">
                <StatusIcon className={`w-16 h-16 mx-auto mb-4 ${statusInfo.color} ${existingApplication.status === 'pending' ? 'animate-spin' : ''}`} />
                <p className={`text-xl font-bold ${statusInfo.color}`}>{statusInfo.text}</p>
                <p className="text-gray-500 text-sm mt-2">
                  Подана: {new Date(existingApplication.created_at).toLocaleDateString('ru-RU')}
                </p>
                {existingApplication.admin_comment && (
                  <div className="mt-4 p-3 bg-white/5 rounded text-sm text-gray-400">
                    {existingApplication.admin_comment}
                  </div>
                )}
              </div>
              
              <button
                onClick={onClose}
                className="w-full py-3 bg-white/10 hover:bg-white/20 text-white font-medium rounded transition-colors"
              >
                Закрыть
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  // Show success state
  if (submitted) {
    return (
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
            onClick={onClose}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#0a0a0a] border border-white/10 rounded-lg p-6 w-full max-w-md text-center"
              onClick={e => e.stopPropagation()}
            >
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-white mb-2">Заявка отправлена!</h2>
              <p className="text-gray-400 mb-6">
                Мы рассмотрим вашу заявку в течение 24-48 часов и свяжемся с вами.
              </p>
              <button
                onClick={onClose}
                className="w-full py-3 bg-pandora-cyan hover:bg-pandora-cyan/80 text-black font-medium rounded transition-colors"
              >
                Отлично!
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    );
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-[#0a0a0a] border border-white/10 rounded-lg p-6 w-full max-w-lg my-8"
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <Star className="text-pandora-cyan" size={24} />
                <h2 className="text-lg font-bold text-white">VIP-партнёрство</h2>
              </div>
              <button onClick={onClose} className="text-gray-500 hover:text-white">
                <X size={20} />
              </button>
            </div>

            {/* Benefits */}
            <div className="bg-white/5 rounded-lg p-4 mb-6 text-sm">
              <p className="text-white font-medium mb-2">Преимущества VIP-партнёра:</p>
              <ul className="text-gray-400 space-y-1">
                <li>• Повышенные комиссии с рефералов</li>
                <li>• Персональный менеджер</li>
                <li>• Приоритетная поддержка</li>
                <li>• Эксклюзивные акции и бонусы</li>
              </ul>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={e => handleChange('email', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-pandora-cyan focus:outline-none"
                  placeholder="your@email.com"
                />
              </div>

              {/* Phone */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Телефон *</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={e => handleChange('phone', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-pandora-cyan focus:outline-none"
                  placeholder="+7 (999) 123-45-67"
                />
              </div>

              {/* Source */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Источник аудитории *</label>
                <select
                  value={formData.source}
                  onChange={e => handleChange('source', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-pandora-cyan focus:outline-none"
                >
                  <option value="" className="bg-[#0a0a0a]">Выберите...</option>
                  {AUDIENCE_SOURCES.map(s => (
                    <option key={s.value} value={s.value} className="bg-[#0a0a0a]">{s.label}</option>
                  ))}
                </select>
              </div>

              {/* Audience Size */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Размер аудитории *</label>
                <select
                  value={formData.audienceSize}
                  onChange={e => handleChange('audienceSize', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-pandora-cyan focus:outline-none"
                >
                  <option value="" className="bg-[#0a0a0a]">Выберите...</option>
                  {AUDIENCE_SIZES.map(s => (
                    <option key={s.value} value={s.value} className="bg-[#0a0a0a]">{s.label}</option>
                  ))}
                </select>
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Расскажите о себе *</label>
                <textarea
                  value={formData.description}
                  onChange={e => handleChange('description', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-pandora-cyan focus:outline-none resize-none"
                  rows={3}
                  placeholder="Чем занимаетесь, какой контент создаёте..."
                />
              </div>

              {/* Expected Volume (optional) */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Ожидаемый объём продаж (опционально)</label>
                <input
                  type="text"
                  value={formData.expectedVolume || ''}
                  onChange={e => handleChange('expectedVolume', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm focus:border-pandora-cyan focus:outline-none"
                  placeholder="Например: 10-20 заказов в месяц"
                />
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-center gap-2 text-red-500 text-sm">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 bg-pandora-cyan hover:bg-pandora-cyan/80 disabled:bg-gray-700 disabled:cursor-not-allowed text-black font-medium rounded transition-colors flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Отправка...
                  </>
                ) : (
                  <>
                    <Send size={18} />
                    Отправить заявку
                  </>
                )}
              </button>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PartnerApplicationModal;
