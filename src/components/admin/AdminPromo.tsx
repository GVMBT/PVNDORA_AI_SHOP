/**
 * AdminPromo Component
 * 
 * Управление промокодами.
 */

import React, { useState, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Tag, Plus, Trash2, Check, X, 
  Calendar, Users, Percent, ToggleLeft, ToggleRight, Package, ShoppingCart
} from 'lucide-react';

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
  onCreatePromo?: (data: Omit<PromoCodeData, 'id' | 'usage_count' | 'created_at'>) => Promise<void>;
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
  const [newCode, setNewCode] = useState('');
  const [newDiscount, setNewDiscount] = useState(10);
  const [newLimit, setNewLimit] = useState<number | undefined>();
  const [newExpiry, setNewExpiry] = useState('');
  const [newProductId, setNewProductId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newCode.trim() || !onCreatePromo) return;
    
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
      setNewCode('');
      setNewDiscount(10);
      setNewLimit(undefined);
      setNewExpiry('');
      setNewProductId(null);
      setIsCreating(false);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!onDeletePromo) return;
    if (confirm('Удалить этот промокод?')) {
      await onDeletePromo(id);
    }
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'Бессрочно';
    return new Date(dateStr).toLocaleDateString('ru-RU');
  };

  return (
    <div className="p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Tag size={20} className="text-pandora-cyan" />
          ПРОМОКОДЫ
        </h2>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-pandora-cyan text-black font-bold text-sm hover:bg-white transition-colors"
        >
          <Plus size={16} /> НОВЫЙ КОД
        </button>
      </div>

      {/* Create Form Modal */}
      <AnimatePresence>
        {isCreating && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <div 
              className="absolute inset-0 bg-black/80 backdrop-blur-sm" 
              onClick={() => !creating && setIsCreating(false)} 
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-md bg-[#080808] border border-pandora-cyan/30 p-6 shadow-2xl"
            >
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold text-white">Новый промокод</h3>
                <button 
                  onClick={() => !creating && setIsCreating(false)}
                  className="text-gray-500 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-4">
                {/* Code */}
                <div>
                  <label className="text-[10px] text-gray-500 font-mono uppercase block mb-1">
                    Код *
                  </label>
                  <input
                    type="text"
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value.toUpperCase())}
                    placeholder="SUMMER25"
                    className="w-full bg-black border border-white/20 px-3 py-2.5 text-white font-mono focus:border-pandora-cyan focus:outline-none"
                  />
                </div>

                {/* Discount */}
                <div>
                  <label className="text-[10px] text-gray-500 font-mono uppercase block mb-1">
                    Скидка (%)
                  </label>
                  <input
                    type="number"
                    value={newDiscount}
                    onChange={(e) => setNewDiscount(parseInt(e.target.value) || 0)}
                    min={1}
                    max={100}
                    className="w-full bg-black border border-white/20 px-3 py-2.5 text-white font-mono focus:border-pandora-cyan focus:outline-none"
                  />
                </div>

                {/* Product */}
                <div>
                  <label className="text-[10px] text-gray-500 font-mono uppercase block mb-1 flex items-center gap-1">
                    <Package size={12} />
                    Товар (опционально)
                  </label>
                  <select
                    value={newProductId || ''}
                    onChange={(e) => setNewProductId(e.target.value || null)}
                    className="w-full bg-black border border-white/20 px-3 py-2.5 text-white font-mono focus:border-pandora-cyan focus:outline-none"
                  >
                    <option value="">Вся корзина</option>
                    {products.map((product) => (
                      <option key={product.id} value={product.id}>
                        {product.name}
                      </option>
                    ))}
                  </select>
                  <p className="text-[9px] text-gray-600 mt-1">
                    Оставьте пустым для скидки на всю корзину
                  </p>
                </div>

                {/* Usage Limit */}
                <div>
                  <label className="text-[10px] text-gray-500 font-mono uppercase block mb-1">
                    Лимит использований
                  </label>
                  <input
                    type="number"
                    value={newLimit || ''}
                    onChange={(e) => setNewLimit(e.target.value ? parseInt(e.target.value) : undefined)}
                    placeholder="Без ограничений"
                    min={1}
                    className="w-full bg-black border border-white/20 px-3 py-2.5 text-white font-mono focus:border-pandora-cyan focus:outline-none placeholder:text-gray-600"
                  />
                </div>

                {/* Expiry */}
                <div>
                  <label className="text-[10px] text-gray-500 font-mono uppercase block mb-1">
                    Срок действия
                  </label>
                  <input
                    type="date"
                    value={newExpiry}
                    onChange={(e) => setNewExpiry(e.target.value)}
                    className="w-full bg-black border border-white/20 px-3 py-2.5 text-white font-mono focus:border-pandora-cyan focus:outline-none"
                  />
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <button
                    onClick={handleCreate}
                    disabled={!newCode.trim() || creating}
                    className="flex-1 py-2.5 bg-green-500 text-black font-bold text-sm hover:bg-green-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    <Check size={16} /> Создать
                  </button>
                  <button
                    onClick={() => setIsCreating(false)}
                    disabled={creating}
                    className="flex-1 py-2.5 bg-white/10 text-white font-bold text-sm hover:bg-white/20 transition-colors flex items-center justify-center gap-2"
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
      <div className="bg-black/50 border border-white/10 overflow-hidden">
        {/* Desktop Table Header */}
        <div className="hidden md:grid grid-cols-12 gap-2 px-4 py-3 bg-white/5 text-[10px] font-mono text-gray-500 uppercase border-b border-white/10">
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
          <div className="text-center py-12 text-gray-600 font-mono text-sm">
            Нет промокодов
          </div>
        ) : (
          promoCodes.map((promo) => {
            const product = promo.product_id 
              ? products.find(p => p.id === promo.product_id)
              : null;
            
            return (
              <div key={promo.id}>
                {/* Desktop Row */}
                <div className="hidden md:grid grid-cols-12 gap-2 px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors items-center">
                  <div className="col-span-2">
                    <span className="font-mono font-bold text-pandora-cyan">{promo.code}</span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1">
                    <Percent size={12} className="text-green-400" />
                    <span className="text-white font-bold">{promo.discount_percent}%</span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1">
                    {promo.product_id ? (
                      <>
                        <Package size={12} className="text-yellow-400" />
                        <span className="text-yellow-400 text-xs truncate" title={product?.name || promo.product_id}>
                          {product?.name || 'Товар'}
                        </span>
                      </>
                    ) : (
                      <>
                        <ShoppingCart size={12} className="text-gray-400" />
                        <span className="text-gray-400 text-xs">Вся корзина</span>
                      </>
                    )}
                  </div>
                  <div className="col-span-2 flex items-center gap-1">
                    <Users size={12} className="text-gray-400" />
                    <span className="text-gray-300">
                      {promo.usage_count} / {promo.usage_limit || '∞'}
                    </span>
                  </div>
                  <div className="col-span-2 flex items-center gap-1 text-sm">
                    <Calendar size={12} className="text-gray-400" />
                    <span className="text-gray-400">{formatDate(promo.expires_at)}</span>
                  </div>
                  <div className="col-span-1">
                    <button
                      onClick={() => onToggleActive?.(promo.id, !promo.is_active)}
                      className={`flex items-center gap-1 text-sm ${
                        promo.is_active ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {promo.is_active ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                    </button>
                  </div>
                  <div className="col-span-1 flex justify-end gap-2">
                    <button
                      onClick={() => handleDelete(promo.id)}
                      className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Mobile Card */}
                <div className="md:hidden border-b border-white/5 p-4 hover:bg-white/5">
                  <div className="flex justify-between items-start mb-3">
                    <span className="font-mono font-bold text-pandora-cyan text-lg">{promo.code}</span>
                    <button
                      onClick={() => onToggleActive?.(promo.id, !promo.is_active)}
                      className={promo.is_active ? 'text-green-400' : 'text-red-400'}
                    >
                      {promo.is_active ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <Percent size={14} className="text-green-400" />
                      <span className="text-white font-bold">{promo.discount_percent}%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Users size={14} className="text-gray-400" />
                      <span className="text-gray-300">{promo.usage_count} / {promo.usage_limit || '∞'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {promo.product_id ? (
                        <>
                          <Package size={14} className="text-yellow-400" />
                          <span className="text-yellow-400 text-xs truncate">{product?.name || 'Товар'}</span>
                        </>
                      ) : (
                        <>
                          <ShoppingCart size={14} className="text-gray-400" />
                          <span className="text-gray-400 text-xs">Вся корзина</span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar size={14} className="text-gray-400" />
                      <span className="text-gray-400 text-xs">{formatDate(promo.expires_at)}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDelete(promo.id)}
                    className="w-full py-2 text-xs font-bold uppercase text-red-400 border border-red-400/30 hover:bg-red-400/10 transition-colors"
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
