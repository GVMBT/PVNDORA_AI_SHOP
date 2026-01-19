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

import { AnimatePresence, motion } from "framer-motion";
import {
  Clock,
  Coins,
  DollarSign,
  Image as ImageIcon,
  Info,
  Package,
  Plus,
  RefreshCw,
  Save,
  Terminal,
  Trash2,
  Upload,
  Video,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import { useAdminProductsTyped } from "../../hooks/api/useAdminApi";
import type { ProductData } from "./types";

interface ProductModalProps {
  isOpen: boolean;
  product: Partial<ProductData> | null;
  onClose: () => void;
  onSave: (product: Partial<ProductData>) => void;
}

type ProductTab = "general" | "pricing" | "inventory";

interface StockItem {
  id: string;
  content: string;
  status: string;
}

const ProductModal: React.FC<ProductModalProps> = ({ isOpen, product, onClose, onSave }) => {
  const [activeTab, setActiveTab] = useState<ProductTab>("general");
  const [inventoryText, setInventoryText] = useState("");
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [loadingStock, setLoadingStock] = useState(false);
  const [addingStock, setAddingStock] = useState(false);
  const { addStockBulk, deleteStockItem, getStock } = useAdminProductsTyped();
  const [editingProduct, setEditingProduct] = useState<Partial<ProductData>>(
    product || {
      name: "",
      price: 0,
      category: "ai",
      status: "active",
      fulfillmentType: "auto",
      image: "",
    }
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset state when product prop changes
  useEffect(() => {
    if (product) {
      setEditingProduct(product);
    } else {
      setEditingProduct({
        name: "",
        price: 0,
        category: "ai",
        status: "active",
        fulfillmentType: "auto",
        image: "",
      });
    }
    setInventoryText("");
    setStockItems([]);
  }, [product]);

  // Load stock callback (defined before useEffect that uses it)
  const loadStock = useCallback(async () => {
    if (!editingProduct.id || typeof editingProduct.id !== "string") {
      return;
    }
    setLoadingStock(true);
    try {
      const stock = await getStock(editingProduct.id, false); // Get all stock (not just available)
      setStockItems(stock);
    } catch (err) {
      console.error("Failed to load stock:", err);
    } finally {
      setLoadingStock(false);
    }
  }, [editingProduct.id, getStock]);

  // Load stock when inventory tab is active and product has ID
  useEffect(() => {
    if (activeTab === "inventory" && editingProduct.id && typeof editingProduct.id === "string") {
      loadStock();
    }
  }, [activeTab, editingProduct.id, loadStock]);

  const handleAddStock = async () => {
    if (!editingProduct.id || typeof editingProduct.id !== "string") {
      alert("Сначала сохраните товар, чтобы добавить сток");
      return;
    }

    const lines = inventoryText.split("\n").filter((l) => l.trim());
    if (lines.length === 0) {
      alert("Введите данные для добавления");
      return;
    }

    setAddingStock(true);
    try {
      const success = await addStockBulk(editingProduct.id, lines);
      if (success) {
        setInventoryText("");
        await loadStock();
        alert(`Успешно добавлено ${lines.length} единиц стока`);
      } else {
        alert("Ошибка при добавлении стока");
      }
    } catch (err) {
      console.error("Failed to add stock:", err);
      alert("Ошибка при добавлении стока");
    } finally {
      setAddingStock(false);
    }
  };

  const handleDeleteStock = async (stockItemId: string) => {
    if (!confirm("Удалить эту позицию из стока?")) {
      return;
    }

    try {
      const success = await deleteStockItem(stockItemId);
      if (success) {
        await loadStock();
        alert("Позиция удалена");
      } else {
        alert("Ошибка при удалении");
      }
    } catch (err) {
      console.error("Failed to delete stock:", err);
      alert("Ошибка при удалении");
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
      return {
        label: "INSTANT",
        color: "text-green-500",
        bg: "bg-green-500/10 border-green-500/30",
        desc: `${stock} ед. на складе → мгновенная выдача`,
      };
    }
    if (fulfillment > 0) {
      return {
        label: "ON_DEMAND",
        color: "text-yellow-500",
        bg: "bg-yellow-500/10 border-yellow-500/30",
        desc: `Нет на складе → предзаказ (~${fulfillment}ч)`,
      };
    }
    return {
      label: "NO_STOCK",
      color: "text-red-500",
      bg: "bg-red-500/10 border-red-500/30",
      desc: "Сток не настроен",
    };
  };

  const deliveryType = getDeliveryType();

  // Helper to render stock content (avoid nested ternary)
  const renderStockContent = () => {
    if (loadingStock) {
      return <p className="text-gray-500 text-xs">Загрузка...</p>;
    }
    if (stockItems.length === 0) {
      return <p className="text-gray-500 text-xs">Сток пуст</p>;
    }
    return (
      <div className="max-h-48 space-y-2 overflow-y-auto">
        {stockItems.map((item) => (
          <div
            className="flex items-start justify-between gap-2 rounded-sm border border-white/5 bg-black/50 p-2"
            key={item.id}
          >
            <code className="flex-1 break-all font-mono text-[10px] text-green-400">
              {item.content}
            </code>
            <div className="flex flex-shrink-0 items-center gap-2">
              <span className="rounded bg-gray-900 px-1.5 py-0.5 font-mono text-[9px] text-gray-500">
                {item.status}
              </span>
              {item.status === "available" && (
                <button
                  className="p-1 text-red-400 hover:text-red-300"
                  onClick={() => handleDeleteStock(item.id)}
                  title="Удалить"
                  type="button"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (!isOpen) {
    return null;
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
        <button
          aria-label="Close modal"
          className="absolute inset-0 cursor-default bg-black/80 backdrop-blur-sm"
          onClick={onClose}
          type="button"
        />
        <motion.div
          animate={{ scale: 1, opacity: 1 }}
          className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto border border-white/20 bg-[#080808] p-6 shadow-2xl"
          exit={{ scale: 0.9, opacity: 0 }}
          initial={{ scale: 0.9, opacity: 0 }}
        >
          {/* Заголовок */}
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="font-bold font-display text-white text-xl">
                {editingProduct?.id ? `РЕДАКТИРОВАНИЕ: ${editingProduct.name}` : "НОВЫЙ ТОВАР"}
              </h3>
              {editingProduct?.id && (
                <p className="mt-1 font-mono text-[10px] text-gray-500">ID: {editingProduct.id}</p>
              )}
            </div>
            <button
              className="rounded p-2 transition-colors hover:bg-white/10"
              onClick={onClose}
              type="button"
            >
              <X className="text-gray-500" size={20} />
            </button>
          </div>

          {/* Индикатор типа доставки (автоматический) */}
          <div
            className={`mb-6 border p-3 ${deliveryType.bg} flex items-center justify-between rounded-sm`}
          >
            <div className="flex items-center gap-3">
              <Zap className={deliveryType.color} size={16} />
              <div>
                <span className={`font-bold font-mono text-xs ${deliveryType.color}`}>
                  РЕЖИМ_ДОСТАВКИ: {deliveryType.label}
                </span>
                <p className="mt-0.5 text-[10px] text-gray-500">{deliveryType.desc}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-gray-500">
              <Info size={12} />
              Авто
            </div>
          </div>

          {/* Вкладки */}
          <div className="mb-6 flex gap-1 border-white/10 border-b">
            {[
              { id: "general" as const, label: "Основное", icon: Package },
              { id: "pricing" as const, label: "Цены", icon: DollarSign },
              { id: "inventory" as const, label: "Склад", icon: Terminal },
            ].map((tab) => (
              <button
                className={`flex items-center gap-2 px-4 py-2 font-bold text-xs uppercase transition-colors ${
                  activeTab === tab.id
                    ? "border-pandora-cyan border-b-2 bg-pandora-cyan/5 text-pandora-cyan"
                    : "text-gray-500 hover:text-white"
                }`}
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                type="button"
              >
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Содержимое вкладок */}
          {activeTab === "general" && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Медиа */}
              <div className="col-span-1 rounded-sm border border-white/10 bg-[#050505] p-4 md:col-span-2">
                <h4 className="mb-3 flex items-center gap-2 font-mono text-gray-500 text-xs uppercase">
                  <ImageIcon size={14} /> Медиа
                </h4>
                <div className="flex items-start gap-4">
                  {/* Загрузка изображения */}
                  <button
                    className="group relative flex h-32 w-32 cursor-pointer items-center justify-center rounded-sm border border-white/20 bg-black transition-colors hover:border-pandora-cyan"
                    onClick={triggerFileInput}
                    type="button"
                  >
                    {editingProduct?.image ? (
                      <img
                        alt="Товар"
                        className="h-full w-full rounded-sm object-cover opacity-80 transition-opacity group-hover:opacity-100"
                        src={editingProduct.image}
                      />
                    ) : (
                      <div className="text-center text-gray-500 group-hover:text-pandora-cyan">
                        <Upload className="mx-auto mb-1" size={24} />
                        <span className="text-[9px] uppercase">Загрузить</span>
                      </div>
                    )}
                  </button>
                  <input
                    accept="image/*"
                    className="hidden"
                    onChange={handleImageUpload}
                    ref={fileInputRef}
                    type="file"
                  />

                  {/* URL */}
                  <div className="flex-1 space-y-3">
                    <div>
                      <label
                        className="mb-1 block text-[10px] text-gray-500 uppercase"
                        htmlFor="product-image-url"
                      >
                        URL изображения
                      </label>
                      <input
                        className="w-full rounded-sm border border-white/20 bg-black p-2 text-white text-xs outline-none focus:border-pandora-cyan"
                        id="product-image-url"
                        onChange={(e) =>
                          setEditingProduct({ ...editingProduct, image: e.target.value })
                        }
                        placeholder="https://..."
                        type="text"
                        value={editingProduct?.image || ""}
                      />
                    </div>
                    <div>
                      <label
                        className="mb-1 flex items-center gap-1 text-[10px] text-gray-500 uppercase"
                        htmlFor="product-video-url"
                      >
                        <Video size={10} /> URL видео (опционально)
                      </label>
                      <input
                        className="w-full rounded-sm border border-white/20 bg-black p-2 text-white text-xs outline-none focus:border-pandora-cyan"
                        id="product-video-url"
                        onChange={(e) =>
                          setEditingProduct({ ...editingProduct, video: e.target.value })
                        }
                        placeholder="https://youtube.com/... или .webm/.mp4"
                        type="text"
                        value={editingProduct?.video || ""}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Название */}
              <div className="col-span-1 md:col-span-2">
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-name"
                >
                  Название товара *
                </label>
                <input
                  className="w-full rounded-sm border border-white/20 bg-black p-2.5 text-sm text-white outline-none focus:border-pandora-cyan"
                  id="product-name"
                  onChange={(e) => setEditingProduct({ ...editingProduct, name: e.target.value })}
                  placeholder="например: Cursor IDE (7 дней)"
                  type="text"
                  value={editingProduct?.name || ""}
                />
              </div>

              {/* Описание */}
              <div className="col-span-1 md:col-span-2">
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-description"
                >
                  Описание
                </label>
                <textarea
                  className="h-20 w-full resize-none rounded-sm border border-white/20 bg-black p-2 text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-description"
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, description: e.target.value })
                  }
                  placeholder="Описание товара..."
                  value={editingProduct?.description || ""}
                />
              </div>

              {/* Категория */}
              <div>
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-category"
                >
                  Категория *
                </label>
                <select
                  className="w-full rounded-sm border border-white/20 bg-black p-2.5 text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-category"
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, category: e.target.value })
                  }
                  value={editingProduct?.category || "ai"}
                >
                  <option value="ai">AI & Текст</option>
                  <option value="dev">Разработка</option>
                  <option value="design">Дизайн & Графика</option>
                  <option value="music">Аудио & Музыка</option>
                </select>
              </div>

              {/* Статус */}
              <div>
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-status"
                >
                  Статус
                </label>
                <select
                  className="w-full rounded-sm border border-white/20 bg-black p-2.5 text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-status"
                  onChange={(e) => setEditingProduct({ ...editingProduct, status: e.target.value })}
                  value={editingProduct?.status || "active"}
                >
                  <option value="active">Активен (виден)</option>
                  <option value="inactive">Неактивен (скрыт)</option>
                  <option value="discontinued">Снят с продажи</option>
                </select>
              </div>

              {/* Тип выдачи */}
              <div>
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-fulfillment-type"
                >
                  Тип выдачи
                </label>
                <select
                  className="w-full rounded-sm border border-white/20 bg-black p-2.5 text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-fulfillment-type"
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, fulfillmentType: e.target.value })
                  }
                  value={editingProduct?.fulfillmentType || "auto"}
                >
                  <option value="auto">Автоматически (из склада)</option>
                  <option value="manual">Вручную (админ отправляет)</option>
                </select>
                <p className="mt-1 text-[9px] text-gray-600">
                  Авто: данные из stock_items • Вручную: админ отправляет сам
                </p>
              </div>

              {/* Время выполнения (для предзаказов) */}
              <div>
                <label
                  className="mb-1 block flex items-center gap-1 text-[10px] text-gray-500 uppercase"
                  htmlFor="product-fulfillment-hours"
                >
                  <Clock size={10} /> Время выполнения (часов)
                </label>
                <input
                  className="w-full rounded-sm border border-white/20 bg-black p-2.5 text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-fulfillment-hours"
                  min={0}
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, fulfillment: Number(e.target.value) })
                  }
                  type="number"
                  value={editingProduct?.fulfillment || 0}
                />
                <p className="mt-1 text-[9px] text-gray-600">
                  Для предзаказов (0 = только при наличии стока)
                </p>
              </div>

              {/* Срок действия */}
              <div>
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-duration"
                >
                  Срок действия (дней)
                </label>
                <input
                  className="w-full rounded-sm border border-white/20 bg-black p-2.5 text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-duration"
                  min={1}
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, duration: Number(e.target.value) })
                  }
                  type="number"
                  value={editingProduct?.duration || 30}
                />
                <p className="mt-1 text-[9px] text-gray-600">Длительность подписки/лицензии</p>
              </div>

              {/* Гарантия */}
              <div>
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-warranty"
                >
                  Гарантия (дней)
                </label>
                <input
                  className="w-full rounded-sm border border-white/20 bg-black p-2.5 text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-warranty"
                  min={0}
                  onChange={(e) => setWarrantyDays(Number(e.target.value))}
                  type="number"
                  value={warrantyDays}
                />
                <p className="mt-1 text-[9px] text-gray-600">Период гарантийной замены</p>
              </div>

              {/* Инструкции */}
              <div className="col-span-1 md:col-span-2">
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="product-instructions"
                >
                  Инструкция по активации
                </label>
                <textarea
                  className="h-24 w-full resize-none rounded-sm border border-white/20 bg-black p-2 font-mono text-white text-xs outline-none focus:border-pandora-cyan"
                  id="product-instructions"
                  onChange={(e) =>
                    setEditingProduct({ ...editingProduct, instructions: e.target.value })
                  }
                  placeholder="1. Перейдите на https://...&#10;2. Введите данные&#10;3. ..."
                  value={editingProduct?.instructions || ""}
                />
              </div>
            </div>
          )}

          {activeTab === "pricing" && (
            <div className="space-y-6">
              {/* Основные цены (RUB) */}
              <div className="rounded-sm border border-white/10 bg-[#050505] p-4">
                <h4 className="mb-4 flex items-center gap-2 font-mono text-gray-500 text-xs uppercase">
                  <Coins size={14} /> Цены (₽)
                </h4>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <div>
                    <label
                      className="mb-1 block text-[10px] text-gray-500 uppercase"
                      htmlFor="product-price"
                    >
                      Цена (₽) *
                    </label>
                    <div className="relative">
                      <span className="absolute top-1/2 left-2 -translate-y-1/2 text-gray-500 text-xs">
                        ₽
                      </span>
                      <input
                        className="w-full rounded-sm border border-white/20 bg-black p-2.5 pl-6 font-mono text-pandora-cyan text-sm outline-none focus:border-pandora-cyan"
                        id="product-price"
                        min={0}
                        onChange={(e) =>
                          setEditingProduct({ ...editingProduct, price: Number(e.target.value) })
                        }
                        step="1"
                        type="number"
                        value={editingProduct?.price || 0}
                      />
                    </div>
                    <p className="mt-1 text-[9px] text-gray-600">Основная цена в рублях</p>
                  </div>

                  <div>
                    <label
                      className="mb-1 block text-[10px] text-gray-500 uppercase"
                      htmlFor="product-msrp"
                    >
                      MSRP (зачёркнутая)
                    </label>
                    <div className="relative">
                      <span className="absolute top-1/2 left-2 -translate-y-1/2 text-gray-500 text-xs">
                        ₽
                      </span>
                      <input
                        className="w-full rounded-sm border border-white/20 bg-black p-2.5 pl-6 font-mono text-gray-400 text-sm line-through outline-none focus:border-pandora-cyan"
                        id="product-msrp"
                        min={0}
                        onChange={(e) =>
                          setEditingProduct({ ...editingProduct, msrp: Number(e.target.value) })
                        }
                        step="1"
                        type="number"
                        value={editingProduct?.msrp || 0}
                      />
                    </div>
                    <p className="mt-1 text-[9px] text-gray-600">
                      Показывается зачёркнутой если &gt; цены
                    </p>
                  </div>

                  <div>
                    <label
                      className="mb-1 block text-[10px] text-yellow-500 uppercase"
                      htmlFor="product-discount-price"
                    >
                      Цена скидочного канала
                    </label>
                    <div className="relative">
                      <span className="absolute top-1/2 left-2 -translate-y-1/2 text-gray-500 text-xs">
                        ₽
                      </span>
                      <input
                        className="w-full rounded-sm border border-yellow-500/30 bg-black p-2.5 pl-6 font-mono text-sm text-yellow-500 outline-none focus:border-yellow-500"
                        id="product-discount-price"
                        min={0}
                        onChange={(e) =>
                          setEditingProduct({
                            ...editingProduct,
                            discountPrice: Number(e.target.value),
                          })
                        }
                        step="1"
                        type="number"
                        value={editingProduct?.discountPrice || 0}
                      />
                    </div>
                    <p className="mt-1 text-[9px] text-gray-600">Цена для скидочного бота</p>
                  </div>
                </div>
              </div>

              {/* Себестоимость и маржа */}
              <div className="rounded-sm border border-white/10 bg-[#050505] p-4">
                <h4 className="mb-4 flex items-center gap-2 font-mono text-gray-500 text-xs uppercase">
                  <Terminal size={14} /> Себестоимость и маржа (внутреннее)
                </h4>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <label
                      className="mb-1 block text-[10px] text-gray-500 uppercase"
                      htmlFor="product-cost-price"
                    >
                      Себестоимость (₽)
                    </label>
                    <div className="relative">
                      <span className="absolute top-1/2 left-2 -translate-y-1/2 text-gray-500 text-xs">
                        ₽
                      </span>
                      <input
                        className="w-full rounded-sm border border-white/20 bg-black p-2.5 pl-6 font-mono text-red-400 text-sm outline-none focus:border-pandora-cyan"
                        id="product-cost-price"
                        min={0}
                        onChange={(e) =>
                          setEditingProduct({
                            ...editingProduct,
                            costPrice: Number(e.target.value),
                          })
                        }
                        step="1"
                        type="number"
                        value={editingProduct?.costPrice || 0}
                      />
                    </div>
                    <p className="mt-1 text-[9px] text-gray-600">Ваши затраты на единицу</p>
                  </div>

                  <div>
                    <span className="mb-1 block text-[10px] text-gray-500 uppercase">Маржа</span>
                    <div className="rounded-sm border border-white/10 bg-black/50 p-2.5">
                      {editingProduct?.price && editingProduct?.costPrice ? (
                        <>
                          <span className="font-mono text-green-500 text-sm">
                            {Math.round(editingProduct.price - editingProduct.costPrice)} ₽
                          </span>
                          <span className="ml-2 text-gray-500 text-xs">
                            (
                            {(
                              ((editingProduct.price - editingProduct.costPrice) /
                                editingProduct.price) *
                              100
                            ).toFixed(0)}
                            %)
                          </span>
                        </>
                      ) : (
                        <span className="font-mono text-gray-600 text-sm">—</span>
                      )}
                    </div>
                    <p className="mt-1 text-[9px] text-gray-600">
                      Рассчитывается: цена - себестоимость
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "inventory" && (
            <div className="space-y-4">
              {/* Текущий сток */}
              <div className="rounded-sm border border-white/10 bg-[#050505] p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="mb-1 font-mono text-gray-500 text-xs uppercase">Текущий сток</h4>
                    <span
                      className={`font-bold font-mono text-2xl ${
                        (editingProduct?.stock || 0) > 0 ? "text-green-500" : "text-red-500"
                      }`}
                    >
                      {editingProduct?.stock || 0}
                    </span>
                    <span className="ml-2 text-gray-500 text-xs">единиц доступно</span>
                  </div>
                  {editingProduct?.sold && editingProduct.sold > 0 && (
                    <div className="text-right">
                      <h4 className="mb-1 font-mono text-gray-500 text-xs uppercase">Продано</h4>
                      <span className="font-bold font-mono text-2xl text-pandora-cyan">
                        {editingProduct.sold}
                      </span>
                    </div>
                  )}
                </div>
                <p className="mt-3 border-white/10 border-t pt-3 text-[9px] text-gray-600">
                  Сток считается из таблицы stock_items. Добавьте данные ниже для пополнения.
                </p>
              </div>

              {/* Текущий сток */}
              {editingProduct.id && (
                <div className="mb-4 rounded-sm border border-blue-500/20 bg-[#050505] p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="flex items-center gap-2 font-mono text-blue-500 text-xs">
                      <Package size={12} /> ТЕКУЩИЙ СТОК
                    </span>
                    <button
                      className="flex items-center gap-1 font-mono text-[10px] text-gray-400 hover:text-blue-400 disabled:opacity-50"
                      disabled={loadingStock}
                      onClick={loadStock}
                      type="button"
                    >
                      <RefreshCw className={loadingStock ? "animate-spin" : ""} size={10} />{" "}
                      Обновить
                    </button>
                  </div>
                  {renderStockContent()}
                </div>
              )}

              {/* Массовая загрузка */}
              <div className="rounded-sm border border-green-500/20 bg-[#050505] p-4">
                <div className="mb-3 flex items-center justify-between">
                  <span className="flex items-center gap-2 font-mono text-green-500 text-xs">
                    <Terminal size={12} /> МАССОВАЯ ЗАГРУЗКА ДАННЫХ
                  </span>
                  <span className="font-mono text-[10px] text-gray-500">
                    {inventoryText.split("\n").filter((l) => l.trim()).length} ЗАПИСЕЙ
                  </span>
                </div>
                <textarea
                  className="h-48 w-full resize-none rounded-sm border border-white/10 bg-black p-3 font-mono text-green-400 text-xs outline-none focus:border-green-500/50"
                  onChange={(e) => setInventoryText(e.target.value)}
                  placeholder={`Вставьте данные, по одному на строку:
user@email.com:password123
api_key_abc123
license_key_xyz789`}
                  value={inventoryText}
                />
                <p className="mt-2 text-[9px] text-gray-600">
                  Каждая строка = 1 единица стока. Добавляется через API /api/admin/stock/bulk
                </p>
              </div>

              <div className="mt-4 flex justify-end">
                <button
                  className="flex items-center gap-2 rounded-sm bg-green-600 px-6 py-2 font-bold text-black text-xs uppercase transition-colors hover:bg-green-500 disabled:cursor-not-allowed disabled:bg-gray-700 disabled:text-gray-500"
                  disabled={!(inventoryText.trim() && editingProduct.id) || addingStock}
                  onClick={handleAddStock}
                  type="button"
                >
                  {addingStock ? (
                    <>
                      <RefreshCw className="animate-spin" size={14} /> Добавление...
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
          <div className="mt-8 flex items-center justify-between border-white/10 border-t pt-4">
            <p className="text-[10px] text-gray-600">* Обязательные поля</p>
            <div className="flex gap-3">
              <button
                className="rounded-sm border border-white/10 px-4 py-2 font-bold text-gray-400 text-xs transition-colors hover:border-white/30 hover:text-white"
                onClick={onClose}
                type="button"
              >
                ОТМЕНА
              </button>
              <button
                className="flex items-center gap-2 rounded-sm bg-pandora-cyan px-6 py-2 font-bold text-black text-xs transition-colors hover:bg-white"
                onClick={() => onSave(editingProduct)}
                type="button"
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
