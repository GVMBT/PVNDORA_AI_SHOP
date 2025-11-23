import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle, Copy } from 'lucide-react';

const PaymentPage = () => {
    const [searchParams] = useSearchParams();
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('idle'); // idle, processing, success, error
    const [paymentMethod, setPaymentMethod] = useState('sbp'); // sbp, crypto

    // Mock Data (would come from URL params in real app)
    const productId = searchParams.get('id') || '123';
    const price = searchParams.get('price') || '300';
    const title = searchParams.get('title') || 'Flux Pro (1 Month)';

    useEffect(() => {
        // Initialize Telegram WebApp
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }
    }, []);

    const handlePayment = async () => {
        setLoading(true);
        setStatus('processing');

        // Simulate API call
        setTimeout(() => {
            setLoading(false);
            setStatus('success');
            if (window.Telegram?.WebApp) {
                window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
            }
        }, 2000);
    };

    if (status === 'success') {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background">
                <div className="bg-surface p-8 rounded-2xl shadow-xl flex flex-col items-center text-center max-w-sm w-full border border-white/5">
                    <CheckCircle className="w-16 h-16 text-success mb-4" />
                    <h2 className="text-2xl font-bold mb-2">Оплата прошла!</h2>
                    <p className="text-gray-400 mb-6">Ваш доступ уже в боте.</p>
                    <button
                        onClick={() => window.Telegram?.WebApp?.close()}
                        className="w-full bg-surface hover:bg-slate-700 text-white font-medium py-3 px-4 rounded-xl transition-colors"
                    >
                        Закрыть
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background p-4 flex flex-col">
            {/* Receipt Card */}
            <div className="bg-surface rounded-2xl p-6 shadow-lg border border-white/5 relative overflow-hidden mb-6">
                {/* Receipt jagged edge effect (visual only) */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-white/10 to-transparent opacity-50"></div>

                <div className="text-center mb-6">
                    <div className="text-gray-400 text-sm uppercase tracking-wider mb-1">К оплате</div>
                    <div className="text-4xl font-bold text-white">{price} ₽</div>
                </div>

                <div className="space-y-3 border-t border-dashed border-gray-700 pt-4">
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Товар</span>
                        <span className="font-medium">{title}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-400">ID заказа</span>
                        <span className="font-mono text-xs bg-black/30 px-2 py-1 rounded text-gray-300">#{productId.slice(0, 8)}</span>
                    </div>
                </div>
            </div>

            {/* Payment Methods */}
            <div className="space-y-3 mb-auto">
                <label className="text-sm font-medium text-gray-400 ml-1">Способ оплаты</label>

                <button
                    onClick={() => setPaymentMethod('sbp')}
                    className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${paymentMethod === 'sbp'
                            ? 'bg-primary/10 border-primary text-white'
                            : 'bg-surface border-transparent text-gray-400 hover:bg-surface/80'
                        }`}
                >
                    <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${paymentMethod === 'sbp' ? 'border-primary' : 'border-gray-500'
                            }`}>
                            {paymentMethod === 'sbp' && <div className="w-2 h-2 bg-primary rounded-full" />}
                        </div>
                        <span className="font-medium">СБП (Карта)</span>
                    </div>
                    <span className="text-xs bg-success/20 text-success px-2 py-1 rounded">0%</span>
                </button>

                <button
                    onClick={() => setPaymentMethod('crypto')}
                    className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${paymentMethod === 'crypto'
                            ? 'bg-primary/10 border-primary text-white'
                            : 'bg-surface border-transparent text-gray-400 hover:bg-surface/80'
                        }`}
                >
                    <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${paymentMethod === 'crypto' ? 'border-primary' : 'border-gray-500'
                            }`}>
                            {paymentMethod === 'crypto' && <div className="w-2 h-2 bg-primary rounded-full" />}
                        </div>
                        <span className="font-medium">Crypto (USDT)</span>
                    </div>
                </button>
            </div>

            {/* Pay Button */}
            <button
                onClick={handlePayment}
                disabled={loading}
                className="w-full bg-primary hover:bg-blue-600 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-blue-500/20 active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-6"
            >
                {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                    <>
                        Оплатить {price} ₽
                    </>
                )}
            </button>

            <p className="text-center text-xs text-gray-500 mt-4">
                Нажимая кнопку, вы соглашаетесь с условиями оферты
            </p>
        </div>
    );
};

export default PaymentPage;
