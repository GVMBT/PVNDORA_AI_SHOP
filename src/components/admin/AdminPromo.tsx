/**
 * AdminPromo Component
 * 
 * Promo codes management for admin panel.
 */

import React, { useState, memo } from 'react';
import { motion } from 'framer-motion';
import { 
  Tag, Plus, Trash2, Edit2, Check, X, 
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
  product_id?: string | null;  // NULL = cart-wide, NOT NULL = product-specific
  created_at: string;
}

interface AdminPromoProps {
  promoCodes: PromoCodeData[];
  products?: Array<{ id: string; name: string }>;  // Products list for product selection
  onCreatePromo?: (data: Omit<PromoCodeData, 'id' | 'usage_count' | 'created_at'>) => Promise<void>;
  onUpdatePromo?: (id: string, data: Partial<PromoCodeData>) => Promise<void>;
  onDeletePromo?: (id: string) => Promise<void>;
  onToggleActive?: (id: string, isActive: boolean) => Promise<void>;
}

const AdminPromo: React.FC<AdminPromoProps> = ({
  promoCodes,
  products = [],  // Products list for product selection (passed from parent)
  onCreatePromo,
  onUpdatePromo,
  onDeletePromo,
  onToggleActive,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [newCode, setNewCode] = useState('');
  const [newDiscount, setNewDiscount] = useState(10);
  const [newLimit, setNewLimit] = useState<number | undefined>();
  const [newExpiry, setNewExpiry] = useState('');
  const [newProductId, setNewProductId] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!newCode.trim() || !onCreatePromo) return;
    
    await onCreatePromo({
      code: newCode.toUpperCase(),
      discount_percent: newDiscount,
      usage_limit: newLimit,
      expires_at: newExpiry || null,
      product_id: newProductId || null,  // NULL = cart-wide, NOT NULL = product-specific
      is_active: true,
    });
    
    setNewCode('');
    setNewDiscount(10);
    setNewLimit(undefined);
    setNewExpiry('');
    setNewProductId(null);
    setIsCreating(false);
  };

  const handleDelete = async (id: string) => {
    if (!onDeletePromo) return;
    if (confirm('Delete this promo code?')) {
      await onDeletePromo(id);
    }
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('ru-RU');
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Tag size={20} className="text-pandora-cyan" />
          PROMO_CODES
        </h2>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-pandora-cyan text-black font-bold text-sm hover:bg-white transition-colors"
        >
          <Plus size={16} /> NEW CODE
        </button>
      </div>

      {/* Create Form */}
      {isCreating && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/5 border border-pandora-cyan/30 p-4 mb-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="text-[10px] text-gray-500 font-mono uppercase">Code</label>
              <input
                type="text"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value.toUpperCase())}
                placeholder="SUMMER25"
                className="w-full bg-black border border-white/20 px-3 py-2 text-white font-mono focus:border-pandora-cyan focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 font-mono uppercase">Discount %</label>
              <input
                type="number"
                value={newDiscount}
                onChange={(e) => setNewDiscount(parseInt(e.target.value) || 0)}
                min={1}
                max={100}
                className="w-full bg-black border border-white/20 px-3 py-2 text-white font-mono focus:border-pandora-cyan focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 font-mono uppercase flex items-center gap-1">
                <Package size={12} />
                Product (Optional)
              </label>
              <select
                value={newProductId || ''}
                onChange={(e) => setNewProductId(e.target.value || null)}
                className="w-full bg-black border border-white/20 px-3 py-2 text-white font-mono focus:border-pandora-cyan focus:outline-none"
              >
                <option value="">All Products (Cart-wide)</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-gray-500 font-mono uppercase">Usage Limit</label>
              <input
                type="number"
                value={newLimit || ''}
                onChange={(e) => setNewLimit(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="Unlimited"
                className="w-full bg-black border border-white/20 px-3 py-2 text-white font-mono focus:border-pandora-cyan focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] text-gray-500 font-mono uppercase">Expires</label>
              <input
                type="date"
                value={newExpiry}
                onChange={(e) => setNewExpiry(e.target.value)}
                className="w-full bg-black border border-white/20 px-3 py-2 text-white font-mono focus:border-pandora-cyan focus:outline-none"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleCreate}
              className="flex items-center gap-2 px-4 py-2 bg-green-500 text-black font-bold text-sm hover:bg-green-400 transition-colors"
            >
              <Check size={16} /> CREATE
            </button>
            <button
              onClick={() => setIsCreating(false)}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 text-white font-bold text-sm hover:bg-white/20 transition-colors"
            >
              <X size={16} /> CANCEL
            </button>
          </div>
        </motion.div>
      )}

      {/* Promo Codes Table */}
      <div className="bg-black/50 border border-white/10 overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-12 gap-2 px-4 py-3 bg-white/5 text-[10px] font-mono text-gray-500 uppercase border-b border-white/10">
          <div className="col-span-2">Code</div>
          <div className="col-span-2">Discount</div>
          <div className="col-span-2">Product</div>
          <div className="col-span-2">Usage</div>
          <div className="col-span-2">Expires</div>
          <div className="col-span-1">Status</div>
          <div className="col-span-1 text-right">Actions</div>
        </div>

        {/* Rows */}
        {promoCodes.length === 0 ? (
          <div className="text-center py-12 text-gray-600 font-mono text-sm">
            NO_PROMO_CODES
          </div>
        ) : (
          promoCodes.map((promo) => {
            // Find product name for product-specific promo codes
            const product = promo.product_id 
              ? products.find(p => p.id === promo.product_id)
              : null;
            
            return (
              <div
                key={promo.id}
                className="grid grid-cols-12 gap-2 px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors items-center"
              >
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
                        {product?.name || 'Product'}
                      </span>
                    </>
                  ) : (
                    <>
                      <ShoppingCart size={12} className="text-gray-400" />
                      <span className="text-gray-400 text-xs">Cart-wide</span>
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
            );
          })
        )}
      </div>
    </div>
  );
};

export default memo(AdminPromo);
