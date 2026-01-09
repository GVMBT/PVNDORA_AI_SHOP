/**
 * ProductModal Component
 * 
 * Modal for creating/editing products.
 * 
 * Field mapping (Frontend → Database):
 * - category → type (ai, dev, design, music)
 * - fulfillmentType → fulfillment_type (auto, manual)
 * - price → price
 * - msrp → msrp (strike-through price, shown when msrp > price)
 * - discountPrice → discount_price (price for discount channel)
 * - costPrice → cost_price (cost for accounting)
 * - warranty → warranty_hours
 * - duration → duration_days
 * - fulfillment → fulfillment_time_hours (time for on-demand orders)
 * - status → status (active, inactive, discontinued)
 * - requiresPrepayment → requires_prepayment
 * - prepaymentPercent → prepayment_percent
 * 
 * Note: Delivery type (instant/preorder) is determined automatically:
 * - If stock > 0 → INSTANT_DEPLOY
 * - If stock = 0 && fulfillment > 0 → ON_DEMAND (preorder)
 * - If stock = 0 && fulfillment = 0 → DISCONTINUED
 */

import React, { useState, useRef, memo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Plus, Terminal, Image as ImageIcon, Upload, Video, DollarSign, Info, Zap, Clock, Package } from 'lucide-react';
import type { ProductData } from './types';

interface ProductModalProps {
  isOpen: boolean;
  product: Partial<ProductData> | null;
  onClose: () => void;
  onSave: (product: Partial<ProductData>) => void;
}

type ProductTab = 'general' | 'pricing' | 'inventory';

const ProductModal: React.FC<ProductModalProps> = ({
  isOpen,
  product,
  onClose,
  onSave,
}) => {
  const [activeTab, setActiveTab] = useState<ProductTab>('general');
  const [inventoryText, setInventoryText] = useState('');
  const [editingProduct, setEditingProduct] = useState<Partial<ProductData>>(
    product || {
      name: '',
      price: 0,
      category: 'ai',
      status: 'active',
      fulfillmentType: 'auto',
      image: '',
    }
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset state when product prop changes
  useEffect(() => {
    if (product) {
      setEditingProduct(product);
    } else {
      setEditingProduct({
        name: '',
        price: 0,
        category: 'ai',
        status: 'active',
        fulfillmentType: 'auto',
        image: '',
      });
    }
  }, [product, isOpen]);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setEditingProduct({ ...editingProduct, image: reader.result as string });
      };
      reader.readAsDataURL(file);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  // Determine delivery type based on stock (read-only display)
  const getDeliveryType = () => {
    const stock = editingProduct?.stock || 0;
    const fulfillment = editingProduct?.fulfillment || 0;
    
    if (stock > 0) {
      return { label: 'INSTANT', color: 'text-green-500', bg: 'bg-green-500/10 border-green-500/30' };
    } else if (fulfillment > 0) {
      return { label: 'ON_DEMAND', color: 'text-yellow-500', bg: 'bg-yellow-500/10 border-yellow-500/30' };
    } else {
      return { label: 'NO_STOCK', color: 'text-red-500', bg: 'bg-red-500/10 border-red-500/30' };
    }
  };

  const deliveryType = getDeliveryType();

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
        <div 
          className="absolute inset-0 bg-black/80 backdrop-blur-sm" 
          onClick={onClose} 
        />
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }} 
          animate={{ scale: 1, opacity: 1 }} 
          exit={{ scale: 0.9, opacity: 0 }}
          className="relative w-full max-w-3xl bg-[#080808] border border-white/20 p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-xl font-display font-bold text-white">
                {editingProduct?.id ? `EDIT: ${editingProduct.name}` : 'NEW PRODUCT'}
              </h3>
              {editingProduct?.id && (
                <p className="text-[10px] text-gray-500 font-mono mt-1">ID: {editingProduct.id}</p>
              )}
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded transition-colors">
              <X size={20} className="text-gray-500" />
            </button>
          </div>

          {/* Delivery Type Indicator (Auto-calculated) */}
          <div className={`mb-6 p-3 border ${deliveryType.bg} rounded-sm flex items-center justify-between`}>
            <div className="flex items-center gap-3">
              <Zap size={16} className={deliveryType.color} />
              <div>
                <span className={`text-xs font-mono font-bold ${deliveryType.color}`}>
                  DEPLOY_MODE: {deliveryType.label}
                </span>
                <p className="text-[10px] text-gray-500 mt-0.5">
                  {editingProduct?.stock && editingProduct.stock > 0 
                    ? `${editingProduct.stock} units in stock → instant delivery`
                    : editingProduct?.fulfillment && editingProduct.fulfillment > 0
                      ? `No stock → on-demand (~${editingProduct.fulfillment}h)`
                      : 'No stock configured'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-gray-500">
              <Info size={12} />
              Auto-calculated
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 border-b border-white/10 mb-6">
            {[
              { id: 'general' as const, label: 'General', icon: Package },
              { id: 'pricing' as const, label: 'Pricing', icon: DollarSign },
              { id: 'inventory' as const, label: 'Inventory', icon: Terminal },
            ].map(tab => (
              <button 
                key={tab.id}
                onClick={() => setActiveTab(tab.id)} 
                className={`px-4 py-2 text-xs font-bold uppercase flex items-center gap-2 transition-colors ${
                  activeTab === tab.id 
                    ? 'text-pandora-cyan border-b-2 border-pandora-cyan bg-pandora-cyan/5' 
                    : 'text-gray-500 hover:text-white'
                }`}
              >
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === 'general' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Media Section */}
              <div className="col-span-1 md:col-span-2 bg-[#050505] p-4 border border-white/10 rounded-sm">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-3 flex items-center gap-2">
                  <ImageIcon size={14} /> Media Assets
                </h4>
                <div className="flex gap-4 items-start">
                  {/* Image Upload Area */}
                  <div 
                    className="relative group w-32 h-32 bg-black border border-white/20 flex items-center justify-center cursor-pointer hover:border-pandora-cyan transition-colors rounded-sm" 
                    onClick={triggerFileInput}
                  >
                    {editingProduct?.image ? (
                      <img 
                        src={editingProduct.image} 
                        className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity rounded-sm" 
                        alt="Product" 
                      />
                    ) : (
                      <div className="text-center text-gray-500 group-hover:text-pandora-cyan">
                        <Upload size={24} className="mx-auto mb-1" />
                        <span className="text-[9px] uppercase">Upload</span>
                      </div>
                    )}
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      className="hidden" 
                      accept="image/*"
                      onChange={handleImageUpload}
                    />
                  </div>

                  {/* URLs Section */}
                  <div className="flex-1 space-y-3">
                    <div>
                      <label className="text-[10px] text-gray-500 block mb-1 uppercase">
                        Image URL
                      </label>
                      <input 
                        type="text" 
                        value={editingProduct?.image || ''} 
                        onChange={(e) => setEditingProduct({...editingProduct, image: e.target.value})}
                        className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                        placeholder="https://..."
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-gray-500 mb-1 uppercase flex items-center gap-1">
                        <Video size={10} /> Video URL (optional)
                      </label>
                      <input 
                        type="text" 
                        value={editingProduct?.video || ''}
                        onChange={(e) => setEditingProduct({...editingProduct, video: e.target.value})}
                        className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                        placeholder="https://youtube.com/... or .webm/.mp4"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Product Name */}
              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Product Name *</label>
                <input 
                  type="text" 
                  value={editingProduct?.name || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, name: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-sm text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  placeholder="e.g. Cursor IDE (7 day)"
                />
              </div>

              {/* Description */}
              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Description</label>
                <textarea 
                  value={editingProduct?.description || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, description: e.target.value})}
                  className="w-full h-20 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none rounded-sm" 
                  placeholder="Product description..." 
                />
              </div>

              {/* Category */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Category *</label>
                <select 
                  value={editingProduct?.category || 'ai'}
                  onChange={(e) => setEditingProduct({...editingProduct, category: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm"
                >
                  <option value="ai">AI & Text</option>
                  <option value="dev">Development</option>
                  <option value="design">Design & Image</option>
                  <option value="music">Audio & Music</option>
                </select>
              </div>

              {/* Status */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Status</label>
                <select 
                  value={editingProduct?.status || 'active'}
                  onChange={(e) => setEditingProduct({...editingProduct, status: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm"
                >
                  <option value="active">Active (Visible)</option>
                  <option value="inactive">Inactive (Hidden)</option>
                  <option value="discontinued">Discontinued</option>
                </select>
              </div>

              {/* Fulfillment Type */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Fulfillment Type</label>
                <select 
                  value={editingProduct?.fulfillmentType || 'auto'}
                  onChange={(e) => setEditingProduct({...editingProduct, fulfillmentType: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm"
                >
                  <option value="auto">Auto (from stock_items)</option>
                  <option value="manual">Manual (admin delivers)</option>
                </select>
                <p className="text-[9px] text-gray-600 mt-1">
                  Auto: credentials from stock_items • Manual: admin sends manually
                </p>
              </div>

              {/* Fulfillment Time (for on-demand) */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase flex items-center gap-1">
                  <Clock size={10} /> Fulfillment Time (hours)
                </label>
                <input 
                  type="number" 
                  value={editingProduct?.fulfillment || 0}
                  onChange={(e) => setEditingProduct({...editingProduct, fulfillment: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  min={0}
                />
                <p className="text-[9px] text-gray-600 mt-1">
                  Time to fulfill on-demand orders (0 = instant only)
                </p>
              </div>

              {/* Duration */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Duration (days)</label>
                <input 
                  type="number" 
                  value={editingProduct?.duration || 30}
                  onChange={(e) => setEditingProduct({...editingProduct, duration: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  min={1}
                />
                <p className="text-[9px] text-gray-600 mt-1">
                  Subscription/license duration
                </p>
              </div>

              {/* Warranty */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Warranty (hours)</label>
                <input 
                  type="number" 
                  value={editingProduct?.warranty || 168}
                  onChange={(e) => setEditingProduct({...editingProduct, warranty: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  min={0}
                />
                <p className="text-[9px] text-gray-600 mt-1">
                  Replacement guarantee period (168h = 7 days)
                </p>
              </div>

              {/* Instructions */}
              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Access Instructions</label>
                <textarea 
                  value={editingProduct?.instructions || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, instructions: e.target.value})}
                  className="w-full h-24 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none rounded-sm font-mono" 
                  placeholder="1. Go to https://...&#10;2. Enter credentials&#10;3. ..." 
                />
              </div>
            </div>
          )}

          {activeTab === 'pricing' && (
            <div className="space-y-6">
              {/* Main Pricing */}
              <div className="bg-[#050505] p-4 border border-white/10 rounded-sm">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
                  <DollarSign size={14} /> Main Pricing
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Price (USD) *</label>
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">$</span>
                      <input 
                        type="number" 
                        value={editingProduct?.price || 0}
                        onChange={(e) => setEditingProduct({...editingProduct, price: Number(e.target.value)})}
                        className="w-full bg-black border border-white/20 p-2.5 pl-6 text-sm text-pandora-cyan font-mono focus:border-pandora-cyan outline-none rounded-sm" 
                        step="0.01"
                        min={0}
                      />
                    </div>
                    <p className="text-[9px] text-gray-600 mt-1">
                      Main selling price
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">MSRP (Strike Price)</label>
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">$</span>
                      <input 
                        type="number" 
                        value={editingProduct?.msrp || 0}
                        onChange={(e) => setEditingProduct({...editingProduct, msrp: Number(e.target.value)})}
                        className="w-full bg-black border border-white/20 p-2.5 pl-6 text-sm text-gray-400 line-through font-mono focus:border-pandora-cyan outline-none rounded-sm" 
                        step="0.01"
                        min={0}
                      />
                    </div>
                    <p className="text-[9px] text-gray-600 mt-1">
                      Original price (crossed out if &gt; price)
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-yellow-500 block mb-1 uppercase">Discount Channel Price</label>
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">$</span>
                      <input 
                        type="number" 
                        value={editingProduct?.discountPrice || 0}
                        onChange={(e) => setEditingProduct({...editingProduct, discountPrice: Number(e.target.value)})}
                        className="w-full bg-black border border-yellow-500/30 p-2.5 pl-6 text-sm text-yellow-500 font-mono focus:border-yellow-500 outline-none rounded-sm" 
                        step="0.01"
                        min={0}
                      />
                    </div>
                    <p className="text-[9px] text-gray-600 mt-1">
                      Price for discount bot channel
                    </p>
                  </div>
                </div>
              </div>

              {/* Cost & Margin */}
              <div className="bg-[#050505] p-4 border border-white/10 rounded-sm">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
                  <Terminal size={14} /> Cost & Margin (Internal)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Cost Price (USD)</label>
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">$</span>
                      <input 
                        type="number" 
                        value={editingProduct?.costPrice || 0}
                        onChange={(e) => setEditingProduct({...editingProduct, costPrice: Number(e.target.value)})}
                        className="w-full bg-black border border-white/20 p-2.5 pl-6 text-sm text-red-400 font-mono focus:border-pandora-cyan outline-none rounded-sm" 
                        step="0.01"
                        min={0}
                      />
                    </div>
                    <p className="text-[9px] text-gray-600 mt-1">
                      Your acquisition cost
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Margin</label>
                    <div className="p-2.5 bg-black/50 border border-white/10 rounded-sm">
                      {editingProduct?.price && editingProduct?.costPrice ? (
                        <>
                          <span className="text-sm font-mono text-green-500">
                            ${(editingProduct.price - editingProduct.costPrice).toFixed(2)}
                          </span>
                          <span className="text-xs text-gray-500 ml-2">
                            ({(((editingProduct.price - editingProduct.costPrice) / editingProduct.price) * 100).toFixed(0)}%)
                          </span>
                        </>
                      ) : (
                        <span className="text-sm font-mono text-gray-600">—</span>
                      )}
                    </div>
                    <p className="text-[9px] text-gray-600 mt-1">
                      Calculated: price - cost
                    </p>
                  </div>
                </div>
              </div>

              {/* Prepayment Settings */}
              <div className="bg-[#050505] p-4 border border-white/10 rounded-sm">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
                  <Clock size={14} /> Prepayment (On-Demand)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-center gap-3 p-3 bg-black border border-white/20 rounded-sm">
                    <input 
                      type="checkbox" 
                      id="requiresPrepayment"
                      checked={editingProduct?.requiresPrepayment || false}
                      onChange={(e) => setEditingProduct({...editingProduct, requiresPrepayment: e.target.checked})}
                      className="accent-pandora-cyan w-4 h-4" 
                    />
                    <label htmlFor="requiresPrepayment" className="text-xs text-white uppercase font-bold cursor-pointer">
                      Requires Prepayment
                    </label>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Prepayment %</label>
                    <input 
                      type="number" 
                      value={editingProduct?.prepaymentPercent || 100}
                      onChange={(e) => setEditingProduct({...editingProduct, prepaymentPercent: Number(e.target.value)})}
                      className="w-full bg-black border border-white/20 p-2.5 text-sm text-white font-mono focus:border-pandora-cyan outline-none rounded-sm disabled:opacity-50" 
                      min={0}
                      max={100}
                      disabled={!editingProduct?.requiresPrepayment}
                    />
                    <p className="text-[9px] text-gray-600 mt-1">
                      % to pay upfront for preorders
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'inventory' && (
            <div className="space-y-4">
              {/* Current Stock Info */}
              <div className="bg-[#050505] p-4 border border-white/10 rounded-sm">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="text-xs font-mono text-gray-500 uppercase mb-1">Current Stock</h4>
                    <span className={`text-2xl font-mono font-bold ${
                      (editingProduct?.stock || 0) > 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {editingProduct?.stock || 0}
                    </span>
                    <span className="text-xs text-gray-500 ml-2">units available</span>
                  </div>
                  {editingProduct?.sold && editingProduct.sold > 0 && (
                    <div className="text-right">
                      <h4 className="text-xs font-mono text-gray-500 uppercase mb-1">Sold</h4>
                      <span className="text-2xl font-mono font-bold text-pandora-cyan">
                        {editingProduct.sold}
                      </span>
                    </div>
                  )}
                </div>
                <p className="text-[9px] text-gray-600 mt-3 border-t border-white/10 pt-3">
                  Stock is calculated from stock_items table. Add credentials below to increase stock.
                </p>
              </div>

              {/* Bulk Upload */}
              <div className="bg-[#050505] p-4 border border-green-500/20 rounded-sm">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-xs font-mono text-green-500 flex items-center gap-2">
                    <Terminal size={12} /> BULK CREDENTIAL UPLOAD
                  </span>
                  <span className="text-[10px] text-gray-500 font-mono">
                    {inventoryText.split('\n').filter(l => l.trim()).length} ITEMS DETECTED
                  </span>
                </div>
                <textarea 
                  value={inventoryText}
                  onChange={(e) => setInventoryText(e.target.value)}
                  placeholder={`Paste credentials here, one per line:
user@email.com:password123
api_key_abc123
license_key_xyz789`}
                  className="w-full h-48 bg-black border border-white/10 p-3 text-xs font-mono text-green-400 focus:border-green-500/50 outline-none resize-none rounded-sm"
                />
                <p className="text-[9px] text-gray-600 mt-2">
                  Each line = 1 stock item. Will be added via /api/admin/stock/bulk endpoint.
                </p>
              </div>
              
              <div className="flex justify-end">
                <button 
                  onClick={() => {
                    // This should trigger the bulk upload API
                    // For now, just show count
                    const lines = inventoryText.split('\n').filter(l => l.trim());
                    if (lines.length > 0) {
                      alert(`Will add ${lines.length} items via API.\nNote: Save product first, then use Inventory tab to add stock.`);
                    }
                  }}
                  disabled={!inventoryText.trim()}
                  className="bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-black disabled:text-gray-500 font-bold py-2 px-6 text-xs uppercase flex items-center gap-2 rounded-sm transition-colors"
                >
                  <Plus size={14} /> Add to Stock
                </button>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 pt-4 border-t border-white/10 flex justify-between items-center">
            <p className="text-[10px] text-gray-600">
              * Required fields
            </p>
            <div className="flex gap-3">
              <button 
                onClick={onClose} 
                className="px-4 py-2 border border-white/10 text-xs font-bold text-gray-400 hover:text-white hover:border-white/30 rounded-sm transition-colors"
              >
                CANCEL
              </button>
              <button 
                onClick={() => onSave(editingProduct)} 
                className="px-6 py-2 bg-pandora-cyan text-black text-xs font-bold hover:bg-white flex items-center gap-2 rounded-sm transition-colors"
              >
                <Save size={14} /> SAVE PRODUCT
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default memo(ProductModal);
