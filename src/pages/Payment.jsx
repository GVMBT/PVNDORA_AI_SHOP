/**
 * Payment Page Component
 * 
 * Handles product display and payment flow in Mini App
 */
import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShoppingCart, Tag, Star, Clock, Shield, Loader2 } from 'lucide-react';
import { useTelegram } from '../hooks/useTelegram';
import { getProduct, createOrder, setAuthHeader } from '../api/client';

export default function Payment() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { 
        isReady, 
        initData, 
        user,
        showMainButton, 
        hideMainButton,
        hapticFeedback,
        showAlert,
        colorScheme,
        startParam
    } = useTelegram();
    
    const [product, setProduct] = useState(null);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const [promoCode, setPromoCode] = useState('');
    const [error, setError] = useState(null);
    
    // Get product ID from URL or start param
    const productId = searchParams.get('product') || startParam;
    
    // Set auth header when ready
    useEffect(() => {
        if (initData) {
            setAuthHeader(initData);
        }
    }, [initData]);
    
    // Load product data
    useEffect(() => {
        async function loadProduct() {
            if (!productId) {
                setError('No product specified');
                setLoading(false);
                return;
            }
            
            try {
                const data = await getProduct(productId);
                setProduct(data);
            } catch (err) {
                console.error('Failed to load product:', err);
                setError('Failed to load product');
            } finally {
                setLoading(false);
            }
        }
        
        if (isReady) {
            loadProduct();
        }
    }, [isReady, productId]);
    
    // Setup main button
    useEffect(() => {
        if (product && product.stock_count > 0 && !processing) {
            const buttonText = user?.language_code === 'ru' 
                ? `💳 Оплатить ${product.price}₽`
                : `💳 Pay $${product.price}`;
            
            showMainButton(buttonText, handlePayment);
        } else {
            hideMainButton();
        }
        
        return () => hideMainButton();
    }, [product, processing, user]);
    
    // Handle payment
    async function handlePayment() {
        if (processing) return;
        
        setProcessing(true);
        hapticFeedback('medium');
        
        try {
            const order = await createOrder(productId, promoCode || null);
            
            hapticFeedback('success');
            
            // Redirect to payment URL
            if (order.payment_url) {
                window.location.href = order.payment_url;
            }
        } catch (err) {
            console.error('Payment failed:', err);
            hapticFeedback('error');
            showAlert(user?.language_code === 'ru' 
                ? 'Ошибка оплаты. Попробуйте снова.' 
                : 'Payment failed. Please try again.');
        } finally {
            setProcessing(false);
        }
    }
    
    // Loading state
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--tg-theme-bg-color)]">
                <Loader2 className="w-8 h-8 animate-spin text-[var(--tg-theme-button-color)]" />
            </div>
        );
    }
    
    // Error state
    if (error || !product) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[var(--tg-theme-bg-color)] p-4">
                <div className="text-center">
                    <p className="text-[var(--tg-theme-hint-color)]">
                        {error || 'Product not found'}
                    </p>
                </div>
            </div>
        );
    }
    
    const isOutOfStock = product.stock_count === 0;
    
    return (
        <div 
            className="min-h-screen p-4 pb-24"
            style={{
                backgroundColor: 'var(--tg-theme-bg-color)',
                color: 'var(--tg-theme-text-color)'
            }}
        >
            {/* Product Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl overflow-hidden"
                style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color)' }}
            >
                {/* Product Header */}
                <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                        <h1 className="text-2xl font-bold">{product.name}</h1>
                        {product.rating > 0 && (
                            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-yellow-500/20">
                                <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                                <span className="text-sm font-medium">{product.rating}</span>
                            </div>
                        )}
                    </div>
                    
                    {/* Price */}
                    <div className="flex items-baseline gap-2 mb-4">
                        <span className="text-3xl font-bold text-[var(--tg-theme-button-color)]">
                            {user?.language_code === 'ru' ? `${product.price}₽` : `$${product.price}`}
                        </span>
                        {product.type && (
                            <span 
                                className="text-sm px-2 py-0.5 rounded-full"
                                style={{ backgroundColor: 'var(--tg-theme-button-color)', color: 'var(--tg-theme-button-text-color)' }}
                            >
                                {product.type}
                            </span>
                        )}
                    </div>
                    
                    {/* Stock status */}
                    <div className={`flex items-center gap-2 text-sm ${isOutOfStock ? 'text-red-500' : 'text-green-500'}`}>
                        <div className={`w-2 h-2 rounded-full ${isOutOfStock ? 'bg-red-500' : 'bg-green-500'}`} />
                        {isOutOfStock 
                            ? (user?.language_code === 'ru' ? 'Нет в наличии' : 'Out of stock')
                            : (user?.language_code === 'ru' ? 'В наличии' : 'In stock')
                        }
                    </div>
                </div>
                
                {/* Description */}
                {product.description && (
                    <div className="px-6 pb-4">
                        <p className="text-[var(--tg-theme-hint-color)]">
                            {product.description}
                        </p>
                    </div>
                )}
                
                {/* Features */}
                <div className="px-6 pb-6 space-y-3">
                    {product.warranty_hours > 0 && (
                        <div className="flex items-center gap-3 text-sm">
                            <Shield className="w-5 h-5 text-[var(--tg-theme-button-color)]" />
                            <span>
                                {user?.language_code === 'ru' 
                                    ? `Гарантия ${product.warranty_hours} ч.`
                                    : `${product.warranty_hours}h warranty`
                                }
                            </span>
                        </div>
                    )}
                    <div className="flex items-center gap-3 text-sm">
                        <Clock className="w-5 h-5 text-[var(--tg-theme-button-color)]" />
                        <span>
                            {user?.language_code === 'ru' 
                                ? 'Мгновенная доставка'
                                : 'Instant delivery'
                            }
                        </span>
                    </div>
                </div>
            </motion.div>
            
            {/* Promo Code Input */}
            {!isOutOfStock && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="mt-4 p-4 rounded-2xl"
                    style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color)' }}
                >
                    <div className="flex items-center gap-2 mb-2">
                        <Tag className="w-4 h-4 text-[var(--tg-theme-hint-color)]" />
                        <span className="text-sm text-[var(--tg-theme-hint-color)]">
                            {user?.language_code === 'ru' ? 'Промокод' : 'Promo code'}
                        </span>
                    </div>
                    <input
                        type="text"
                        value={promoCode}
                        onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                        placeholder={user?.language_code === 'ru' ? 'Введите промокод' : 'Enter promo code'}
                        className="w-full px-4 py-3 rounded-xl border-0 outline-none"
                        style={{
                            backgroundColor: 'var(--tg-theme-bg-color)',
                            color: 'var(--tg-theme-text-color)'
                        }}
                    />
                </motion.div>
            )}
            
            {/* Reviews */}
            {product.reviews && product.reviews.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="mt-4 p-4 rounded-2xl"
                    style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color)' }}
                >
                    <h3 className="font-semibold mb-3">
                        {user?.language_code === 'ru' ? 'Отзывы' : 'Reviews'}
                    </h3>
                    <div className="space-y-3">
                        {product.reviews.slice(0, 3).map((review, i) => (
                            <div key={i} className="text-sm">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className="flex">
                                        {[...Array(5)].map((_, j) => (
                                            <Star
                                                key={j}
                                                className={`w-3 h-3 ${j < review.rating ? 'text-yellow-500 fill-yellow-500' : 'text-gray-400'}`}
                                            />
                                        ))}
                                    </div>
                                    <span className="text-[var(--tg-theme-hint-color)]">
                                        {review.users?.username || review.users?.first_name || 'User'}
                                    </span>
                                </div>
                                {review.text && (
                                    <p className="text-[var(--tg-theme-hint-color)]">
                                        {review.text}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}
            
            {/* Processing Overlay */}
            {processing && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div 
                        className="p-6 rounded-2xl flex flex-col items-center"
                        style={{ backgroundColor: 'var(--tg-theme-bg-color)' }}
                    >
                        <Loader2 className="w-8 h-8 animate-spin text-[var(--tg-theme-button-color)] mb-3" />
                        <span>
                            {user?.language_code === 'ru' ? 'Создание заказа...' : 'Creating order...'}
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}

