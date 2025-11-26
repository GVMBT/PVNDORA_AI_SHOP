/**
 * Orders History Page
 */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Package, Clock, CheckCircle, XCircle, RefreshCw, Loader2 } from 'lucide-react';
import { useTelegram } from '../hooks/useTelegram';
import { getOrders, setAuthHeader } from '../api/client';

const statusConfig = {
    pending: { icon: Clock, color: 'text-yellow-500', label: { en: 'Pending', ru: 'Ожидание' } },
    paid: { icon: RefreshCw, color: 'text-blue-500', label: { en: 'Processing', ru: 'Обработка' } },
    completed: { icon: CheckCircle, color: 'text-green-500', label: { en: 'Completed', ru: 'Завершен' } },
    failed: { icon: XCircle, color: 'text-red-500', label: { en: 'Failed', ru: 'Ошибка' } },
    refunded: { icon: RefreshCw, color: 'text-purple-500', label: { en: 'Refunded', ru: 'Возврат' } }
};

export default function Orders() {
    const { isReady, initData, user, showBackButton, hideBackButton } = useTelegram();
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    
    const lang = user?.language_code || 'en';
    
    useEffect(() => {
        if (initData) {
            setAuthHeader(initData);
        }
    }, [initData]);
    
    useEffect(() => {
        showBackButton(() => window.history.back());
        return () => hideBackButton();
    }, []);
    
    useEffect(() => {
        async function loadOrders() {
            try {
                const data = await getOrders();
                setOrders(data);
            } catch (err) {
                console.error('Failed to load orders:', err);
            } finally {
                setLoading(false);
            }
        }
        
        if (isReady) {
            loadOrders();
        }
    }, [isReady]);
    
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--tg-theme-bg-color)]">
                <Loader2 className="w-8 h-8 animate-spin text-[var(--tg-theme-button-color)]" />
            </div>
        );
    }
    
    return (
        <div 
            className="min-h-screen p-4"
            style={{
                backgroundColor: 'var(--tg-theme-bg-color)',
                color: 'var(--tg-theme-text-color)'
            }}
        >
            <h1 className="text-2xl font-bold mb-6">
                {lang === 'ru' ? 'Мои заказы' : 'My Orders'}
            </h1>
            
            {orders.length === 0 ? (
                <div className="text-center py-12">
                    <Package className="w-12 h-12 mx-auto mb-4 text-[var(--tg-theme-hint-color)]" />
                    <p className="text-[var(--tg-theme-hint-color)]">
                        {lang === 'ru' ? 'У вас пока нет заказов' : 'No orders yet'}
                    </p>
                </div>
            ) : (
                <div className="space-y-3">
                    {orders.map((order, i) => {
                        const status = statusConfig[order.status] || statusConfig.pending;
                        const StatusIcon = status.icon;
                        
                        return (
                            <motion.div
                                key={order.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                className="p-4 rounded-xl"
                                style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color)' }}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <h3 className="font-medium">
                                            {lang === 'ru' ? 'Заказ' : 'Order'} #{order.id.slice(0, 8)}
                                        </h3>
                                        <p className="text-sm text-[var(--tg-theme-hint-color)] mt-1">
                                            {new Date(order.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-bold text-[var(--tg-theme-button-color)]">
                                            {order.amount}₽
                                        </p>
                                        <div className={`flex items-center gap-1 mt-1 ${status.color}`}>
                                            <StatusIcon className="w-4 h-4" />
                                            <span className="text-sm">
                                                {status.label[lang] || status.label.en}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                
                                {order.expires_at && order.status === 'completed' && (
                                    <p className="text-xs text-[var(--tg-theme-hint-color)] mt-2">
                                        {lang === 'ru' ? 'Действует до' : 'Valid until'}: {new Date(order.expires_at).toLocaleDateString()}
                                    </p>
                                )}
                            </motion.div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

