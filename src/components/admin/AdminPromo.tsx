/**
 * AdminPromo Component
 *
 * Управление промокодами.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  Calendar,
  Check,
  Package,
  Percent,
  Plus,
  ShoppingCart,
  Tag,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Users,
  X,
} from "lucide-react";
import type React from "react";
import { memo, useState } from "react";

export interface PromoCodeData {
  id: string;
  code: string;
  discount_percent: number;
  expires_at?: string | null;
  usage_limit?: number | null;
  usage_count: number;
  is_active: boolean;
  product_id?: string | null;
  created_at: string;
}

interface AdminPromoProps {
  promoCodes: PromoCodeData[];
  products?: Array<{ id: string; name: string }>;
  onCreatePromo?: (data: Omit<PromoCodeData, "id" | "usage_count" | "created_at">) => Promise<void>;
  onUpdatePromo?: (id: string, data: Partial<PromoCodeData>) => Promise<void>;
  onDeletePromo?: (id: string) => Promise<void>;
  onToggleActive?: (id: string, isActive: boolean) => Promise<void>;
}

const AdminPromo: React.FC<AdminPromoProps> = ({
  promoCodes,
  products = [],
  onCreatePromo,
  onDeletePromo,
  onToggleActive,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newDiscount, setNewDiscount] = useState(10);
  const [newLimit, setNewLimit] = useState<number | undefined>();
  const [newExpiry, setNewExpiry] = useState("");
  const [newProductId, setNewProductId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!(newCode.trim() && onCreatePromo)) return;

    setCreating(true);
    try {
      await onCreatePromo({
        code: newCode.toUpperCase(),
        discount_percent: newDiscount,
        usage_limit: newLimit,
        expires_at: newExpiry || null,
        product_id: newProductId || null,
        is_active: true,
      });

      // Reset form
      setNewCode("");
      setNewDiscount(10);
      setNewLimit(undefined);
      setNewExpiry("");
      setNewProductId(null);
      setIsCreating(false);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!onDeletePromo) return;
    if (confirm("Удалить этот промокод?")) {
      await onDeletePromo(id);
    }
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "Бессрочно";
    return new Date(dateStr).toLocaleDateString("ru-RU");
  };

  return (
    <div className="p-4 md:p-6">
      {/* Header */}
      <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <h2 className="flex items-center gap-2 font-bold text-white text-xl">
          <Tag className="text-pandora-cyan" size={20} />
          ПРОМОКОДЫ
        </h2>
        <button
          className="flex items-center gap-2 bg-pandora-cyan px-4 py-2 font-bold text-black text-sm transition-colors hover:bg-white"
          onClick={() => setIsCreating(true)}
          type="button"
        >
          <Plus size={16} /> НОВЫЙ КОД
        </button>
      </div>

      {/* Create Form Modal */}
      <AnimatePresence>
        {isCreating && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <button
              aria-label="Close modal"
              className="absolute inset-0 cursor-default bg-black/80 backdrop-blur-sm"
              onClick={() => !creating && setIsCreating(false)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && !creating) setIsCreating(false);
              }}
              type="button"
            />
            <motion.div
              animate={{ scale: 1, opacity: 1 }}
              className="relative w-full max-w-md border border-pandora-cyan/30 bg-[#080808] p-6 shadow-2xl"
              exit={{ scale: 0.9, opacity: 0 }}
              initial={{ scale: 0.9, opacity: 0 }}
            >
              <div className="mb-6 flex items-center justify-between">
                <h3 className="font-bold text-lg text-white">Новый промокод</h3>
                <button
                  className="text-gray-500 hover:text-white"
                  onClick={() => !creating && setIsCreating(false)}
                  type="button"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-4">
                {/* Code */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 uppercase"
                    htmlFor="promo-code"
                  >
                    Код *
                  </label>
                  <input
                    className="w-full border border-white/20 bg-black px-3 py-2.5 font-mono text-white focus:border-pandora-cyan focus:outline-none"
                    id="promo-code"
                    onChange={(e) => setNewCode(e.target.value.toUpperCase())}
                    placeholder="SUMMER25"
                    type="text"
                    value={newCode}
                  />
                </div>

                {/* Discount */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 uppercase"
                    htmlFor="promo-discount"
                  >
                    Скидка (%)
                  </label>
                  <input
                    className="w-full border border-white/20 bg-black px-3 py-2.5 font-mono text-white focus:border-pandora-cyan focus:outline-none"
                    id="promo-discount"
                    max={100}
                    min={1}
                    onChange={(e) => setNewDiscount(Number.parseInt(e.target.value, 10) || 0)}
                    type="number"
                    value={newDiscount}
                  />
                </div>

                {/* Product */}
                <div>
                  <label
                    className="mb-1 block flex items-center gap-1 font-mono text-[10px] text-gray-500 uppercase"
                    htmlFor="promo-product"
                  >
                    <Package size={12} />
                    Товар (опционально)
                  </label>
                  <select
                    className="w-full border border-white/20 bg-black px-3 py-2.5 font-mono text-white focus:border-pandora-cyan focus:outline-none"
                    id="promo-product"
                    onChange={(e) => setNewProductId(e.target.value || null)}
                    value={newProductId || ""}
                  >
                    <option value="">Вся корзина</option>
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-[9px] text-gray-600">
                    Оставьте пустым для скидки на всю корзину
                  </p>
                </div>

                {/* Usage Limit */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 uppercase"
                    htmlFor="promo-limit"
                  >
                    Лимит использований
                  </label>
                  <input
                    className="w-full border border-white/20 bg-black px-3 py-2.5 font-mono text-white placeholder:text-gray-600 focus:border-pandora-cyan focus:outline-none"
                    id="promo-limit"
                    min={1}
                    onChange={(e) =>
                      setNewLimit(e.target.value ? Number.parseInt(e.target.value, 10) : undefined)
                    }
                    placeholder="Без ограничений"
                    type="number"
                    value={newLimit || ""}
                  />
                </div>

                {/* Expiry */}
                <div>
                  <label
                    className="mb-1 block font-mono text-[10px] text-gray-500 uppercase"
                    htmlFor="promo-expiry"
                  >
                    Срок действия
                  </label>
                  <input
                    className="w-full border border-white/20 bg-black px-3 py-2.5 font-mono text-white focus:border-pandora-cyan focus:outline-none"
                    id="promo-expiry"
                    onChange={(e) => setNewExpiry(e.target.value)}
                    type="date"
                    value={newExpiry}
                  />
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <button
                    className="flex flex-1 items-center justify-center gap-2 bg-green-500 py-2.5 font-bold text-black text-sm transition-colors hover:bg-green-400 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!newCode.trim() || creating}
                    onClick={handleCreate}
                    type="button"
                  >
                    <Check size={16} /> Создать
                  </button>
                  <button
                    className="flex flex-1 items-center justify-center gap-2 bg-white/10 py-2.5 font-bold text-sm text-white transition-colors hover:bg-white/20"
                    disabled={creating}
                    onClick={() => setIsCreating(false)}
                    type="button"
                  >
                    <X size={16} /> Отмена
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Promo Codes List */}
      <div className="overflow-hidden border border-white/10 bg-black/50">
        {/* Desktop Table Header */}
        <div className="hidden grid-cols-12 gap-2 border-white/10 border-b bg-white/5 px-4 py-3 font-mono text-[10px] text-gray-500 uppercase md:grid">
          <div className="col-span-2">Код</div>
          <div className="col-span-2">Скидка</div>
          <div className="col-span-2">Товар</div>
          <div className="col-span-2">Использовано</div>
          <div className="col-span-2">Истекает</div>
          <div className="col-span-1">Статус</div>
          <div className="col-span-1 text-right">Действие</div>
        </div>

        {/* Rows */}
        {promoCodes.length === 0 ? (
          <div className="py-12 text-center font-mono text-gray-600 text-sm">Нет промокодов</div>
        ) : (
          promoCodes.map((promo) => {
            const product = promo.product_id
              ? products.find((p) => p.id === promo.product_id)
              : null;

            return (
              <div key={promo.id}>
                {/* Desktop Row */}
                <div className="hidden grid-cols-12 items-center gap-2 border-white/5 border-b px-4 py-3 transition-colors hover:bg-white/5 md:grid">
                  <div className="col-span-2">
                    <span className="font-bold font-mono text-pandora-cyan">{promo.code}</span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1">
                    <Percent className="text-green-400" size={12} />
                    <span className="font-bold text-white">{promo.discount_percent}%</span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1">
                    {promo.product_id ? (
                      <>
                        <Package className="text-yellow-400" size={12} />
                        <span
                          className="truncate text-xs text-yellow-400"
                          title={product?.name || promo.product_id}
                        >
                          {product?.name || "Товар"}
                        </span>
                      </>
                    ) : (
                      <>
                        <ShoppingCart className="text-gray-400" size={12} />
                        <span className="text-gray-400 text-xs">Вся корзина</span>
                      </>
                    )}
                  </div>
                  <div className="col-span-2 flex items-center gap-1">
                    <Users className="text-gray-400" size={12} />
                    <span className="text-gray-300">
                      {promo.usage_count} / {promo.usage_limit || "∞"}
                    </span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1 text-sm">
                    <Calendar className="text-gray-400" size={12} />
                    <span className="text-gray-400">{formatDate(promo.expires_at)}</span>
                  </div>
                  <div className="col-span-1">
                    <button
                      className={`flex items-center gap-1 text-sm ${
                        promo.is_active ? "text-green-400" : "text-red-400"
                      }`}
                      onClick={() => onToggleActive?.(promo.id, !promo.is_active)}
                      type="button"
                    >
                      {promo.is_active ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                    </button>
                  </div>
                  <div className="col-span-1 flex justify-end gap-2">
                    <button
                      className="p-1.5 text-gray-500 transition-colors hover:text-red-400"
                      onClick={() => handleDelete(promo.id)}
                      type="button"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Mobile Card */}
                <div className="border-white/5 border-b p-4 hover:bg-white/5 md:hidden">
                  <div className="mb-3 flex items-start justify-between">
                    <span className="font-bold font-mono text-lg text-pandora-cyan">
                      {promo.code}
                    </span>
                    <button
                      className={promo.is_active ? "text-green-400" : "text-red-400"}
                      onClick={() => onToggleActive?.(promo.id, !promo.is_active)}
                      type="button"
                    >
                      {promo.is_active ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                    </button>
                  </div>

                  <div className="mb-3 grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2">
                      <Percent className="text-green-400" size={14} />
                      <span className="font-bold text-white">{promo.discount_percent}%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Users className="text-gray-400" size={14} />
                      <span className="text-gray-300">
                        {promo.usage_count} / {promo.usage_limit || "∞"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {promo.product_id ? (
                        <>
                          <Package className="text-yellow-400" size={14} />
                          <span className="truncate text-xs text-yellow-400">
                            {product?.name || "Товар"}
                          </span>
                        </>
                      ) : (
                        <>
                          <ShoppingCart className="text-gray-400" size={14} />
                          <span className="text-gray-400 text-xs">Вся корзина</span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="text-gray-400" size={14} />
                      <span className="text-gray-400 text-xs">{formatDate(promo.expires_at)}</span>
                    </div>
                  </div>

                  <button
                    className="w-full border border-red-400/30 py-2 font-bold text-red-400 text-xs uppercase transition-colors hover:bg-red-400/10"
                    onClick={() => handleDelete(promo.id)}
                    type="button"
                  >
                    Удалить
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default memo(AdminPromo);
