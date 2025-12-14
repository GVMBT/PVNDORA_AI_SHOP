/**
 * OrderCard Component
 * 
 * Displays a complete order card with header, status banners, and items.
 */

import React, { memo } from 'react';
import { Check, Clock, AlertTriangle, Package, Shield } from 'lucide-react';
import { formatPrice } from '../../utils/currency';
import OrderStatusBadge from './OrderStatusBadge';
import OrderItem, { type OrderItemData } from './OrderItem';

export interface RefundContext {
  orderId: string;
  orderTotal: number;
  productNames: string[];
  reason?: string;
}

type RawOrderStatus = 'pending' | 'prepaid' | 'paid' | 'partial' | 'delivered' | 'cancelled' | 'refunded' | 'expired' | 'failed';

export interface OrderData {
  id: string;
  displayId?: string;
  date: string;
  total: number;
  currency?: string;
  status: 'paid' | 'processing' | 'refunded';
  items: OrderItemData[];
  payment_url?: string | null;
  rawStatus?: RawOrderStatus;
  paymentConfirmed?: boolean;
  statusMessage?: string;
  canCancel?: boolean;
  canRequestRefund?: boolean;
}

interface OrderCardProps {
  order: OrderData;
  revealedKeys: (string | number)[];
  copiedId: string | number | null;
  onToggleReveal: (id: string | number) => void;
  onCopy: (text: string, id: string | number) => void;
  onOpenReview: (itemId: string | number, itemName: string, orderId: string) => void;
  onOpenSupport?: (context?: RefundContext) => void;
}

const OrderCard: React.FC<OrderCardProps> = ({
  order,
  revealedKeys,
  copiedId,
  onToggleReveal,
  onCopy,
  onOpenReview,
  onOpenSupport,
}) => {
  return (
    <div className="relative group">
      {/* Connecting Line */}
      <div className="absolute -left-3 top-0 bottom-0 w-px bg-white/5 group-hover:bg-white/10 transition-colors" />

      {/* Order Card */}
      <div className="bg-[#080808] border border-white/10 hover:border-white/20 transition-all relative overflow-hidden">
        {/* Card Header */}
        <div className="bg-white/5 p-3 flex justify-between items-center border-b border-white/5">
          <div className="flex items-center gap-4">
            <span className="font-mono text-xs text-pandora-cyan tracking-wider">
              ID: {order.displayId || order.id}
            </span>
            <span className="hidden sm:inline text-[10px] font-mono text-gray-600 uppercase">
              // {order.date}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <OrderStatusBadge rawStatus={order.rawStatus} status={order.status} />
            <span className="font-display font-bold text-white">
              {formatPrice(order.total, order.currency || 'USD')}
            </span>
          </div>
        </div>

        {/* Status Explanation Banner */}
        {order.statusMessage && order.rawStatus !== 'prepaid' && (
          <div className={`px-4 py-2 text-[10px] font-mono border-b ${
            order.paymentConfirmed 
              ? 'bg-green-500/5 border-green-500/20 text-green-400' 
              : 'bg-orange-500/5 border-orange-500/20 text-orange-400'
          }`}>
            <div className="flex items-center gap-2">
              {order.paymentConfirmed ? <Check size={12} /> : <Clock size={12} />}
              {order.statusMessage}
            </div>
          </div>
        )}

        {/* Payment Button - ONLY for unpaid orders */}
        {order.rawStatus === 'pending' && order.payment_url && (
          <div className="p-4 bg-orange-500/10 border-b border-orange-500/20">
            <div className="flex items-center justify-between">
              <div className="text-[10px] font-mono text-orange-400">
                <span className="flex items-center gap-2">
                  <AlertTriangle size={12} />
                  PAYMENT_REQUIRED — Оплатите заказ
                </span>
              </div>
              <button
                onClick={() => {
                  const tgWebApp = window.Telegram?.WebApp;
                  if (tgWebApp) {
                    tgWebApp.openLink(order.payment_url!);
                  } else {
                    window.location.href = order.payment_url!;
                  }
                }}
                className="px-4 py-2 bg-pandora-cyan text-black font-mono text-xs font-bold uppercase hover:bg-pandora-cyan/80 transition-colors"
              >
                PAY_NOW
              </button>
            </div>
          </div>
        )}
        
        {/* Waiting for Stock Banner - for prepaid orders */}
        {order.rawStatus === 'prepaid' && (
          <div className="p-4 bg-purple-500/10 border-b border-purple-500/20">
            <div className="text-[11px] font-mono text-purple-400">
              <div className="flex items-center gap-2 mb-2">
                <Check size={12} className="text-green-400" />
                <span className="text-green-400">PAYMENT CONFIRMED</span>
              </div>
              <div className="flex items-center gap-2 text-purple-300 mb-2">
                <Package size={12} />
                Товар временно отсутствует на складе. Доставим при поступлении.
              </div>
              <div className="flex items-center gap-2 text-gray-500 text-[10px]">
                <Shield size={10} />
                Автоматический возврат средств при превышении срока доставки
              </div>
            </div>
          </div>
        )}
        
        {/* Warranty Refund Banner - for delivered orders within warranty */}
        {order.rawStatus === 'delivered' && order.canRequestRefund && onOpenSupport && (
          <div className="p-4 bg-green-500/5 border-b border-green-500/20">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-mono text-green-400">
                <div className="flex items-center gap-2">
                  <Shield size={12} />
                  Гарантийный период активен
                </div>
              </div>
              <button
                onClick={() => onOpenSupport({
                  orderId: order.id,
                  orderTotal: order.total,
                  productNames: order.items.map(i => i.name),
                  reason: 'WARRANTY_CLAIM: Проблема с доставленным товаром'
                })}
                className="px-3 py-1.5 bg-green-500/20 border border-green-500/30 text-green-400 font-mono text-[10px] uppercase hover:bg-green-500/30 transition-colors"
              >
                REPORT_ISSUE
              </button>
            </div>
          </div>
        )}

        {/* Items Content */}
        <div className="p-5 space-y-6">
          {order.items.map((item) => (
            <OrderItem
              key={item.id}
              item={item}
              orderId={order.id}
              revealedKeys={revealedKeys}
              copiedId={copiedId}
              onToggleReveal={onToggleReveal}
              onCopy={onCopy}
              onOpenReview={onOpenReview}
            />
          ))}
        </div>
        
        {/* Decorative Corner Overlays */}
        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-pandora-cyan opacity-50" />
        <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-pandora-cyan opacity-50" />
      </div>
    </div>
  );
};

export default memo(OrderCard);


