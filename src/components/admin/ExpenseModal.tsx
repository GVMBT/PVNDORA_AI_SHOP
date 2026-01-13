/**
 * ExpenseModal Component
 *
 * Модальное окно добавления расходов.
 *
 * Категории расходов:
 * - supplier - Поставщики
 * - acquiring - Эквайринг
 * - infrastructure - Инфраструктура
 * - marketing - Маркетинг (списывается из резервов)
 * - salary - Зарплаты
 * - refund - Возвраты
 * - other - Прочее
 */

import { AnimatePresence, motion } from "framer-motion";
import { Calendar, DollarSign, FileText, Save, Tag, X } from "lucide-react";
import type React from "react";
import { memo, useEffect, useState } from "react";

export interface ExpenseData {
  description: string;
  amount: number;
  currency: "USD" | "RUB";
  category:
    | "supplier"
    | "acquiring"
    | "infrastructure"
    | "marketing"
    | "salary"
    | "refund"
    | "other";
  date?: string; // ISO date
  supplier_id?: string;
}

interface ExpenseModalProps {
  isOpen: boolean;
  expense?: ExpenseData | null;
  onClose: () => void;
  onSave: (expense: ExpenseData) => Promise<void>;
}

const EXPENSE_CATEGORIES = [
  { value: "supplier", label: "Поставщики", icon: "📦" },
  { value: "acquiring", label: "Эквайринг", icon: "💳" },
  { value: "infrastructure", label: "Инфраструктура", icon: "⚙️" },
  { value: "marketing", label: "Маркетинг (из резервов)", icon: "📢" },
  { value: "salary", label: "Зарплаты", icon: "💰" },
  { value: "refund", label: "Возвраты", icon: "↩️" },
  { value: "other", label: "Прочее", icon: "📋" },
] as const;

const ExpenseModal: React.FC<ExpenseModalProps> = ({ isOpen, expense, onClose, onSave }) => {
  const [editingExpense, setEditingExpense] = useState<ExpenseData>({
    description: "",
    amount: 0,
    currency: "RUB",
    category: "other",
    date: new Date().toISOString().split("T")[0], // Today in YYYY-MM-DD format
  });
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<keyof ExpenseData, string>>>({});

  // Reset form when modal opens/closes or expense changes
  useEffect(() => {
    if (isOpen) {
      if (expense) {
        setEditingExpense(expense);
      } else {
        setEditingExpense({
          description: "",
          amount: 0,
          currency: "RUB",
          category: "other",
          date: new Date().toISOString().split("T")[0],
        });
      }
      setErrors({});
    }
  }, [isOpen, expense]);

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof ExpenseData, string>> = {};

    if (!editingExpense.description.trim()) {
      newErrors.description = "Описание обязательно";
    }

    if (editingExpense.amount <= 0) {
      newErrors.amount = "Сумма должна быть больше 0";
    }

    if (!editingExpense.date) {
      newErrors.date = "Дата обязательна";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave(editingExpense);
      onClose();
    } catch (error) {
      console.error("Failed to save expense:", error);
      // Error handling can be improved with toast notifications
    } finally {
      setIsSaving(false);
    }
  };

  const handleCategoryChange = (category: ExpenseData["category"]) => {
    setEditingExpense({ ...editingExpense, category });
  };

  const formatMoney = (amount: number, currency: "USD" | "RUB"): string => {
    const symbol = currency === "USD" ? "$" : "₽";
    if (currency === "RUB") {
      return `${Math.round(amount)} ${symbol}`;
    }
    return `${amount.toFixed(2)} ${symbol}`;
  };

  if (!isOpen) return null;

  const selectedCategoryInfo = EXPENSE_CATEGORIES.find((c) => c.value === editingExpense.category);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/80 backdrop-blur-sm"
          onClick={onClose}
        />
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="relative w-full max-w-lg bg-[#080808] border border-white/20 p-6 shadow-2xl z-10"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-display font-bold text-white flex items-center gap-2">
              <DollarSign size={20} className="text-green-400" />
              ДОБАВИТЬ РАСХОД
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="text-gray-500 hover:text-white transition-colors"
              disabled={isSaving}
            >
              <X size={20} />
            </button>
          </div>

          {/* Form */}
          <div className="space-y-4">
            {/* Description */}
            <div>
              <label
                htmlFor="expense-description"
                className="text-[10px] text-gray-500 uppercase mb-1.5 flex items-center gap-1"
              >
                <FileText size={12} />
                Описание
              </label>
              <textarea
                id="expense-description"
                value={editingExpense.description}
                onChange={(e) =>
                  setEditingExpense({ ...editingExpense, description: e.target.value })
                }
                placeholder="Описание расхода..."
                className={`w-full h-20 bg-black border ${
                  errors.description ? "border-red-500" : "border-white/20"
                } p-3 text-white text-sm focus:border-pandora-cyan outline-none resize-none`}
                disabled={isSaving}
              />
              {errors.description && (
                <p className="text-xs text-red-500 mt-1">{errors.description}</p>
              )}
            </div>

            {/* Amount & Currency */}
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label
                  htmlFor="expense-amount"
                  className="text-[10px] text-gray-500 uppercase mb-1.5 flex items-center gap-1"
                >
                  <DollarSign size={12} />
                  Сумма
                </label>
                <input
                  id="expense-amount"
                  type="number"
                  step="0.01"
                  min="0"
                  value={editingExpense.amount || ""}
                  onChange={(e) =>
                    setEditingExpense({
                      ...editingExpense,
                      amount: Number.parseFloat(e.target.value) || 0,
                    })
                  }
                  placeholder="0.00"
                  className={`w-full bg-black border ${
                    errors.amount ? "border-red-500" : "border-white/20"
                  } p-3 text-white text-sm focus:border-pandora-cyan outline-none`}
                  disabled={isSaving}
                />
                {errors.amount && <p className="text-xs text-red-500 mt-1">{errors.amount}</p>}
              </div>
              <div>
                <label
                  htmlFor="currency-select"
                  className="text-[10px] text-gray-500 uppercase mb-1.5 block"
                >
                  Валюта
                </label>
                <select
                  id="currency-select"
                  value={editingExpense.currency}
                  onChange={(e) =>
                    setEditingExpense({
                      ...editingExpense,
                      currency: e.target.value as "USD" | "RUB",
                    })
                  }
                  className="w-full bg-black border border-white/20 p-3 text-white text-sm focus:border-pandora-cyan outline-none"
                  disabled={isSaving}
                >
                  <option value="USD">USD</option>
                  <option value="RUB">RUB</option>
                </select>
              </div>
            </div>

            {/* Category */}
            <div>
              <span className="text-[10px] text-gray-500 uppercase mb-1.5 flex items-center gap-1">
                <Tag size={12} />
                Категория
              </span>
              <div className="grid grid-cols-2 gap-2" role="group" aria-label="Категория расхода">
                {EXPENSE_CATEGORIES.map((cat) => (
                  <button
                    type="button"
                    key={cat.value}
                    onClick={() => handleCategoryChange(cat.value)}
                    className={`p-3 border text-left transition-colors ${
                      editingExpense.category === cat.value
                        ? "border-pandora-cyan bg-pandora-cyan/10 text-pandora-cyan"
                        : "border-white/20 bg-black hover:border-white/40 text-gray-300"
                    }`}
                    disabled={isSaving}
                  >
                    <div className="text-xs font-bold flex items-center gap-2">
                      <span>{cat.icon}</span>
                      {cat.label}
                    </div>
                    {cat.value === "marketing" && (
                      <div className="text-[9px] text-yellow-400 mt-1">Списывается из резервов</div>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Date */}
            <div>
              <label
                htmlFor="expense-date"
                className="text-[10px] text-gray-500 uppercase mb-1.5 flex items-center gap-1"
              >
                <Calendar size={12} />
                Дата
              </label>
              <input
                id="expense-date"
                type="date"
                value={editingExpense.date || ""}
                onChange={(e) => setEditingExpense({ ...editingExpense, date: e.target.value })}
                className={`w-full bg-black border ${
                  errors.date ? "border-red-500" : "border-white/20"
                } p-3 text-white text-sm focus:border-pandora-cyan outline-none`}
                disabled={isSaving}
              />
              {errors.date && <p className="text-xs text-red-500 mt-1">{errors.date}</p>}
            </div>

            {/* Preview */}
            {editingExpense.amount > 0 && (
              <div className="bg-white/5 border border-white/10 p-3">
                <div className="text-[10px] text-gray-500 uppercase mb-1">Предпросмотр</div>
                <div className="text-sm text-white font-mono">
                  {formatMoney(editingExpense.amount, editingExpense.currency)}
                </div>
                {selectedCategoryInfo && (
                  <div className="text-xs text-gray-400 mt-1">
                    {selectedCategoryInfo.icon} {selectedCategoryInfo.label}
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSaving}
                className="flex-1 py-3 bg-white/5 border border-white/20 text-white font-bold text-sm hover:bg-white/10 transition-colors disabled:opacity-50"
              >
                Отмена
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className="flex-1 py-3 bg-pandora-cyan text-black font-bold text-sm hover:bg-pandora-cyan/80 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Save size={16} />
                {isSaving ? "Сохранение..." : "Сохранить"}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default memo(ExpenseModal);
