/**
 * ProductModal Component
 * 
 * Модальное окно создания/редактирования товара.
 * 
 * Маппинг полей (Frontend → База данных):
 * - category → type (ai, dev, design, music)
 * - fulfillmentType → fulfillment_type (auto, manual)
 * - price → price
 * - msrp → msrp (зачёркнутая цена)
 * - discountPrice → discount_price (цена для скидочного канала)
 * - costPrice → cost_price (себестоимость)
 * - warranty → warranty_hours (хранится в часах, UI показывает дни)
 * - duration → duration_days
 * - fulfillment → fulfillment_time_hours
 * 
 * Тип доставки определяется автоматически:
 * - Сток > 0 → INSTANT (мгновенная выдача)
 * - Сток = 0 && fulfillment > 0 → ON_DEMAND (предзаказ)
 * - Сток = 0 && fulfillment = 0 → NO_STOCK (недоступен)
 */

import React, { useState, useRef, memo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Save, Plus, Terminal, Image as ImageIcon, Upload, Video, DollarSign, Info, Zap, Clock, Package, Trash2, RefreshCw } from 'lucide-react';
import type { ProductData } from './types';
import { useAdminProductsTyped } from '../../../hooks/api/useAdminApi';

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
  const [stockItems, setStockItems] = useState<any[]>([]);
  const [loadingStock, setLoadingStock] = useState(false);
  const [addingStock, setAddingStock] = useState(false);
  const { addStockBulk, deleteStockItem, getStock } = useAdminProductsTyped();
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
    setInventoryText('');
    setStockItems([]);
  }, [product, isOpen]);

  // Load stock when inventory tab is active and product has ID
  useEffect(() => {
    if (activeTab === 'inventory' && editingProduct.id && typeof editingProduct.id === 'string') {
      loadStock();
    }
  }, [activeTab, editingProduct.id]);

  const loadStock = async () => {
    if (!editingProduct.id || typeof editingProduct.id !== 'string') return;
    setLoadingStock(true);
    try {
      const stock = await getStock(editingProduct.id, false); // Get all stock (not just available)
      setStockItems(stock);
    } catch (err) {
      console.error('Failed to load stock:', err);
    } finally {
      setLoadingStock(false);
    }
  };

  const handleAddStock = async () => {
    if (!editingProduct.id || typeof editingProduct.id !== 'string') {
      alert('Сначала сохраните товар, чтобы добавить сток');
      return;
    }

    const lines = inventoryText.split('\n').filter(l => l.trim());
    if (lines.length === 0) {
      alert('Введите данные для добавления');
      return;
    }

    setAddingStock(true);
    try {
      const success = await addStockBulk(editingProduct.id, lines);
      if (success) {
        setInventoryText('');
        await loadStock();
        alert(`Успешно добавлено ${lines.length} единиц стока`);
      } else {
        alert('Ошибка при добавлении стока');
      }
    } catch (err) {
      console.error('Failed to add stock:', err);
      alert('Ошибка при добавлении стока');
    } finally {
      setAddingStock(false);
    }
  };

  const handleDeleteStock = async (stockItemId: string) => {
    if (!confirm('Удалить эту позицию из стока?')) return;

    try {
      const success = await deleteStockItem(stockItemId);
      if (success) {
        await loadStock();
        alert('Позиция удалена');
      } else {
        alert('Ошибка при удалении');
      }
    } catch (err) {
      console.error('Failed to delete stock:', err);
      alert('Ошибка при удалении');
    }
  };

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

  // Конвертация гарантии: UI (дни) ↔ DB (часы)
  const warrantyDays = Math.floor((editingProduct?.warranty || 0) / 24);
  const setWarrantyDays = (days: number) => {
    setEditingProduct({ ...editingProduct, warranty: days * 24 });
  };

  // Определение типа доставки (только для отображения)
  const getDeliveryType = () => {
    const stock = editingProduct?.stock || 0;
    const fulfillment = editingProduct?.fulfillment || 0;
    
    if (stock > 0) {
      return { label: 'INSTANT', color: 'text-green-500', bg: 'bg-green-500/10 border-green-500/30', desc: `${stock} ед. на складе → мгновенная выдача` };
    } else if (fulfillment > 0) {
      return { label: 'ON_DEMAND', color: 'text-yellow-500', bg: 'bg-yellow-500/10 border-yellow-500/30', desc: `Нет на складе → предзаказ (~${fulfillment}ч)` };
    } else {
      return { label: 'NO_STOCK', color: 'text-red-500', bg: 'bg-red-500/10 border-red-500/30', desc: 'Сток не настроен' };
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
          {/* Заголовок */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-xl font-display font-bold text-white">
                {editingProduct?.id ? `РЕДАКТИРОВАНИЕ: ${editingProduct.name}` : 'НОВЫЙ ТОВАР'}
              </h3>
              {editingProduct?.id && (
                <p className="text-[10px] text-gray-500 font-mono mt-1">ID: {editingProduct.id}</p>
              )}
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded transition-colors">
              <X size={20} className="text-gray-500" />
            </button>
          </div>

          {/* Индикатор типа доставки (автоматический) */}
          <div className={`mb-6 p-3 border ${deliveryType.bg} rounded-sm flex items-center justify-between`}>
            <div className="flex items-center gap-3">
              <Zap size={16} className={deliveryType.color} />
              <div>
                <span className={`text-xs font-mono font-bold ${deliveryType.color}`}>
                  РЕЖИМ_ДОСТАВКИ: {deliveryType.label}
                </span>
                <p className="text-[10px] text-gray-500 mt-0.5">{deliveryType.desc}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-gray-500">
              <Info size={12} />
              Авто
            </div>
          </div>

          {/* Вкладки */}
          <div className="flex gap-1 border-b border-white/10 mb-6">
            {[
              { id: 'general' as const, label: 'Основное', icon: Package },
              { id: 'pricing' as const, label: 'Цены', icon: DollarSign },
              { id: 'inventory' as const, label: 'Склад', icon: Terminal },
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

          {/* Содержимое вкладок */}
          {activeTab === 'general' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Медиа */}
              <div className="col-span-1 md:col-span-2 bg-[#050505] p-4 border border-white/10 rounded-sm">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-3 flex items-center gap-2">
                  <ImageIcon size={14} /> Медиа
                </h4>
                <div className="flex gap-4 items-start">
                  {/* Загрузка изображения */}
                  <div 
                    className="relative group w-32 h-32 bg-black border border-white/20 flex items-center justify-center cursor-pointer hover:border-pandora-cyan transition-colors rounded-sm" 
                    onClick={triggerFileInput}
                  >
                    {editingProduct?.image ? (
                      <img 
                        src={editingProduct.image} 
                        className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity rounded-sm" 
                        alt="Товар" 
                      />
                    ) : (
                      <div className="text-center text-gray-500 group-hover:text-pandora-cyan">
                        <Upload size={24} className="mx-auto mb-1" />
                        <span className="text-[9px] uppercase">Загрузить</span>
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

                  {/* URL */}
                  <div className="flex-1 space-y-3">
                    <div>
                      <label className="text-[10px] text-gray-500 block mb-1 uppercase">
                        URL изображения
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
                        <Video size={10} /> URL видео (опционально)
                      </label>
                      <input 
                        type="text" 
                        value={editingProduct?.video || ''}
                        onChange={(e) => setEditingProduct({...editingProduct, video: e.target.value})}
                        className="w-full bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                        placeholder="https://youtube.com/... или .webm/.mp4"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Название */}
              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Название товара *</label>
                <input 
                  type="text" 
                  value={editingProduct?.name || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, name: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-sm text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  placeholder="например: Cursor IDE (7 дней)"
                />
              </div>

              {/* Описание */}
              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Описание</label>
                <textarea 
                  value={editingProduct?.description || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, description: e.target.value})}
                  className="w-full h-20 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none rounded-sm" 
                  placeholder="Описание товара..." 
                />
              </div>

              {/* Категория */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Категория *</label>
                <select 
                  value={editingProduct?.category || 'ai'}
                  onChange={(e) => setEditingProduct({...editingProduct, category: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm"
                >
                  <option value="ai">AI & Текст</option>
                  <option value="dev">Разработка</option>
                  <option value="design">Дизайн & Графика</option>
                  <option value="music">Аудио & Музыка</option>
                </select>
              </div>

              {/* Статус */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Статус</label>
                <select 
                  value={editingProduct?.status || 'active'}
                  onChange={(e) => setEditingProduct({...editingProduct, status: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm"
                >
                  <option value="active">Активен (виден)</option>
                  <option value="inactive">Неактивен (скрыт)</option>
                  <option value="discontinued">Снят с продажи</option>
                </select>
              </div>

              {/* Тип выдачи */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Тип выдачи</label>
                <select 
                  value={editingProduct?.fulfillmentType || 'auto'}
                  onChange={(e) => setEditingProduct({...editingProduct, fulfillmentType: e.target.value})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm"
                >
                  <option value="auto">Автоматически (из склада)</option>
                  <option value="manual">Вручную (админ отправляет)</option>
                </select>
                <p className="text-[9px] text-gray-600 mt-1">
                  Авто: данные из stock_items • Вручную: админ отправляет сам
                </p>
              </div>

              {/* Время выполнения (для предзаказов) */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase flex items-center gap-1">
                  <Clock size={10} /> Время выполнения (часов)
                </label>
                <input 
                  type="number" 
                  value={editingProduct?.fulfillment || 0}
                  onChange={(e) => setEditingProduct({...editingProduct, fulfillment: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  min={0}
                />
                <p className="text-[9px] text-gray-600 mt-1">
                  Для предзаказов (0 = только при наличии стока)
                </p>
              </div>

              {/* Срок действия */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Срок действия (дней)</label>
                <input 
                  type="number" 
                  value={editingProduct?.duration || 30}
                  onChange={(e) => setEditingProduct({...editingProduct, duration: Number(e.target.value)})}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  min={1}
                />
                <p className="text-[9px] text-gray-600 mt-1">
                  Длительность подписки/лицензии
                </p>
              </div>

              {/* Гарантия */}
              <div>
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Гарантия (дней)</label>
                <input 
                  type="number" 
                  value={warrantyDays}
                  onChange={(e) => setWarrantyDays(Number(e.target.value))}
                  className="w-full bg-black border border-white/20 p-2.5 text-xs text-white focus:border-pandora-cyan outline-none rounded-sm" 
                  min={0}
                />
                <p className="text-[9px] text-gray-600 mt-1">
                  Период гарантийной замены
                </p>
              </div>

              {/* Инструкции */}
              <div className="col-span-1 md:col-span-2">
                <label className="text-[10px] text-gray-500 block mb-1 uppercase">Инструкция по активации</label>
                <textarea 
                  value={editingProduct?.instructions || ''}
                  onChange={(e) => setEditingProduct({...editingProduct, instructions: e.target.value})}
                  className="w-full h-24 bg-black border border-white/20 p-2 text-xs text-white focus:border-pandora-cyan outline-none resize-none rounded-sm font-mono" 
                  placeholder="1. Перейдите на https://...&#10;2. Введите данные&#10;3. ..." 
                />
              </div>
            </div>
          )}

          {activeTab === 'pricing' && (
            <div className="space-y-6">
              {/* Основные цены */}
              <div className="bg-[#050505] p-4 border border-white/10 rounded-sm">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
                  <DollarSign size={14} /> Базовые цены (USD)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Цена (USD) *</label>
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
                      Основная цена (база для конвертации)
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">MSRP (зачёркнутая)</label>
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
                      Показывается зачёркнутой если &gt; цены
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-yellow-500 block mb-1 uppercase">Цена скидочного канала</label>
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
                      Цена для скидочного бота
                    </p>
                  </div>
                </div>
              </div>

              {/* Якорные цены */}
              <div className="bg-[#050505] p-4 border border-blue-500/20 rounded-sm">
                <h4 className="text-xs font-mono text-blue-400 uppercase mb-4 flex items-center gap-2">
                  <DollarSign size={14} /> Фиксированные цены по валютам (Anchor Prices)
                </h4>
                <p className="text-[10px] text-gray-500 mb-4">
                  Если задана — используется фиксированная цена. Если пусто — автоматическая конвертация из USD.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] text-blue-400 block mb-1 uppercase">Цена в рублях (RUB)</label>
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">₽</span>
                      <input 
                        type="number" 
                        value={editingProduct?.prices?.RUB || ''}
                        onChange={(e) => {
                          const value = e.target.value ? Number(e.target.value) : undefined;
                          const newPrices = { ...(editingProduct?.prices || {}) };
                          if (value !== undefined && value > 0) {
                            newPrices.RUB = value;
                          } else {
                            delete newPrices.RUB;
                          }
                          setEditingProduct({...editingProduct, prices: Object.keys(newPrices).length > 0 ? newPrices : undefined});
                        }}
                        className="w-full bg-black border border-blue-500/30 p-2.5 pl-6 text-sm text-blue-400 font-mono focus:border-blue-500 outline-none rounded-sm" 
                        step="1"
                        min={0}
                        placeholder="Авто из USD"
                      />
                    </div>
                    <p className="text-[9px] text-gray-600 mt-1">
                      Фиксированная цена для RU/BY/KZ пользователей
                    </p>
                  </div>

                  <div>
                    <label className="text-[10px] text-blue-400 block mb-1 uppercase">Цена в долларах (USD) — перезапись</label>
                    <div className="relative">
                      <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">$</span>
                      <input 
                        type="number" 
                        value={editingProduct?.prices?.USD || ''}
                        onChange={(e) => {
                          const value = e.target.value ? Number(e.target.value) : undefined;
                          const newPrices = { ...(editingProduct?.prices || {}) };
                          if (value !== undefined && value > 0) {
                            newPrices.USD = value;
                          } else {
                            delete newPrices.USD;
                          }
                          setEditingProduct({...editingProduct, prices: Object.keys(newPrices).length > 0 ? newPrices : undefined});
                        }}
                        className="w-full bg-black border border-blue-500/30 p-2.5 pl-6 text-sm text-blue-400 font-mono focus:border-blue-500 outline-none rounded-sm" 
                        step="0.01"
                        min={0}
                        placeholder="Использовать базовую"
                      />
                    </div>
                    <p className="text-[9px] text-gray-600 mt-1">
                      Опционально: перезаписать базовую для USD пользователей
                    </p>
                  </div>
                </div>
                
                {/* MSRP Anchor Prices */}
                <div className="mt-6 pt-6 border-t border-blue-500/10">
                  <h5 className="text-[10px] text-blue-300 uppercase mb-3 flex items-center gap-2">
                    MSRP (зачёркнутая цена) по валютам
                  </h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] text-blue-300 block mb-1 uppercase">MSRP в рублях (RUB)</label>
                      <div className="relative">
                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">₽</span>
                        <input 
                          type="number" 
                          value={editingProduct?.msrp_prices?.RUB || ''}
                          onChange={(e) => {
                            const value = e.target.value ? Number(e.target.value) : undefined;
                            const newMsrpPrices = { ...(editingProduct?.msrp_prices || {}) };
                            if (value !== undefined && value > 0) {
                              newMsrpPrices.RUB = value;
                            } else {
                              delete newMsrpPrices.RUB;
                            }
                            setEditingProduct({...editingProduct, msrp_prices: Object.keys(newMsrpPrices).length > 0 ? newMsrpPrices : undefined});
                          }}
                          className="w-full bg-black border border-blue-400/30 p-2.5 pl-6 text-sm text-blue-300 font-mono focus:border-blue-400 outline-none rounded-sm line-through" 
                          step="1"
                          min={0}
                          placeholder="Авто из USD MSRP"
                        />
                      </div>
                      <p className="text-[9px] text-gray-600 mt-1">
                        Фиксированный MSRP для RU/BY/KZ пользователей
                      </p>
                    </div>

                    <div>
                      <label className="text-[10px] text-blue-300 block mb-1 uppercase">MSRP в долларах (USD) — перезапись</label>
                      <div className="relative">
                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-500 text-xs">$</span>
                        <input 
                          type="number" 
                          value={editingProduct?.msrp_prices?.USD || ''}
                          onChange={(e) => {
                            const value = e.target.value ? Number(e.target.value) : undefined;
                            const newMsrpPrices = { ...(editingProduct?.msrp_prices || {}) };
                            if (value !== undefined && value > 0) {
                              newMsrpPrices.USD = value;
                            } else {
                              delete newMsrpPrices.USD;
                            }
                            setEditingProduct({...editingProduct, msrp_prices: Object.keys(newMsrpPrices).length > 0 ? newMsrpPrices : undefined});
                          }}
                          className="w-full bg-black border border-blue-400/30 p-2.5 pl-6 text-sm text-blue-300 font-mono focus:border-blue-400 outline-none rounded-sm line-through" 
                          step="0.01"
                          min={0}
                          placeholder="Использовать базовый MSRP"
                        />
                      </div>
                      <p className="text-[9px] text-gray-600 mt-1">
                        Опционально: перезаписать базовый MSRP для USD пользователей
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="mt-3 p-2 bg-blue-500/5 border border-blue-500/10 rounded-sm">
                  <p className="text-[10px] text-blue-300 font-mono">
                    ℹ️ Якорные цены позволяют задать "красивую" фиксированную цену (990 ₽ вместо 987.34 ₽).
                    Цена не будет меняться при колебаниях курса.
                  </p>
                </div>
              </div>

              {/* Себестоимость и маржа */}
              <div className="bg-[#050505] p-4 border border-white/10 rounded-sm">
                <h4 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
                  <Terminal size={14} /> Себестоимость и маржа (внутреннее)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Себестоимость (USD)</label>
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
                      Ваши затраты на единицу
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-[10px] text-gray-500 block mb-1 uppercase">Маржа</label>
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
                      Рассчитывается: цена - себестоимость
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'inventory' && (
            <div className="space-y-4">
              {/* Текущий сток */}
              <div className="bg-[#050505] p-4 border border-white/10 rounded-sm">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="text-xs font-mono text-gray-500 uppercase mb-1">Текущий сток</h4>
                    <span className={`text-2xl font-mono font-bold ${
                      (editingProduct?.stock || 0) > 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {editingProduct?.stock || 0}
                    </span>
                    <span className="text-xs text-gray-500 ml-2">единиц доступно</span>
                  </div>
                  {editingProduct?.sold && editingProduct.sold > 0 && (
                    <div className="text-right">
                      <h4 className="text-xs font-mono text-gray-500 uppercase mb-1">Продано</h4>
                      <span className="text-2xl font-mono font-bold text-pandora-cyan">
                        {editingProduct.sold}
                      </span>
                    </div>
                  )}
                </div>
                <p className="text-[9px] text-gray-600 mt-3 border-t border-white/10 pt-3">
                  Сток считается из таблицы stock_items. Добавьте данные ниже для пополнения.
                </p>
              </div>

              {/* Текущий сток */}
              {editingProduct.id && (
                <div className="bg-[#050505] p-4 border border-blue-500/20 rounded-sm mb-4">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-mono text-blue-500 flex items-center gap-2">
                      <Package size={12} /> ТЕКУЩИЙ СТОК
                    </span>
                    <button
                      onClick={loadStock}
                      disabled={loadingStock}
                      className="text-[10px] text-gray-400 hover:text-blue-400 font-mono flex items-center gap-1 disabled:opacity-50"
                    >
                      <RefreshCw size={10} className={loadingStock ? 'animate-spin' : ''} /> Обновить
                    </button>
                  </div>
                  {loadingStock ? (
                    <p className="text-xs text-gray-500">Загрузка...</p>
                  ) : stockItems.length === 0 ? (
                    <p className="text-xs text-gray-500">Сток пуст</p>
                  ) : (
                    <div className="max-h-48 overflow-y-auto space-y-2">
                      {stockItems.map((item: any) => (
                        <div
                          key={item.id}
                          className="flex items-start justify-between gap-2 p-2 bg-black/50 border border-white/5 rounded-sm"
                        >
                          <code className="text-[10px] text-green-400 flex-1 break-all font-mono">
                            {item.content}
                          </code>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="text-[9px] text-gray-500 font-mono px-1.5 py-0.5 bg-gray-900 rounded">
                              {item.status}
                            </span>
                            {item.status === 'available' && (
                              <button
                                onClick={() => handleDeleteStock(item.id)}
                                className="text-red-400 hover:text-red-300 p-1"
                                title="Удалить"
                              >
                                <Trash2 size={12} />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Массовая загрузка */}
              <div className="bg-[#050505] p-4 border border-green-500/20 rounded-sm">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-xs font-mono text-green-500 flex items-center gap-2">
                    <Terminal size={12} /> МАССОВАЯ ЗАГРУЗКА ДАННЫХ
                  </span>
                  <span className="text-[10px] text-gray-500 font-mono">
                    {inventoryText.split('\n').filter(l => l.trim()).length} ЗАПИСЕЙ
                  </span>
                </div>
                <textarea 
                  value={inventoryText}
                  onChange={(e) => setInventoryText(e.target.value)}
                  placeholder={`Вставьте данные, по одному на строку:
user@email.com:password123
api_key_abc123
license_key_xyz789`}
                  className="w-full h-48 bg-black border border-white/10 p-3 text-xs font-mono text-green-400 focus:border-green-500/50 outline-none resize-none rounded-sm"
                />
                <p className="text-[9px] text-gray-600 mt-2">
                  Каждая строка = 1 единица стока. Добавляется через API /api/admin/stock/bulk
                </p>
              </div>
              
              <div className="flex justify-end mt-4">
                <button 
                  onClick={handleAddStock}
                  disabled={!inventoryText.trim() || !editingProduct.id || addingStock}
                  className="bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-black disabled:text-gray-500 font-bold py-2 px-6 text-xs uppercase flex items-center gap-2 rounded-sm transition-colors"
                >
                  {addingStock ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" /> Добавление...
                    </>
                  ) : (
                    <>
                      <Plus size={14} /> Добавить на склад
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Подвал */}
          <div className="mt-8 pt-4 border-t border-white/10 flex justify-between items-center">
            <p className="text-[10px] text-gray-600">
              * Обязательные поля
            </p>
            <div className="flex gap-3">
              <button 
                onClick={onClose} 
                className="px-4 py-2 border border-white/10 text-xs font-bold text-gray-400 hover:text-white hover:border-white/30 rounded-sm transition-colors"
              >
                ОТМЕНА
              </button>
              <button 
                onClick={() => onSave(editingProduct)} 
                className="px-6 py-2 bg-pandora-cyan text-black text-xs font-bold hover:bg-white flex items-center gap-2 rounded-sm transition-colors"
              >
                <Save size={14} /> СОХРАНИТЬ
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default memo(ProductModal);
