/**
 * Payment Success Page
 */
import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle } from 'lucide-react';
import { useTelegram } from '../hooks/useTelegram';

export default function Success() {
    const [searchParams] = useSearchParams();
    const { user, showMainButton, close, hapticFeedback } = useTelegram();
    
    const orderId = searchParams.get('order_id');
    const lang = user?.language_code || 'en';
    
    useEffect(() => {
        hapticFeedback('success');
        
        showMainButton(
            lang === 'ru' ? 'Закрыть' : 'Close',
            close
        );
    }, [lang]);
    
    return (
        <div 
            className="min-h-screen flex items-center justify-center p-4"
            style={{
                backgroundColor: 'var(--tg-theme-bg-color)',
                color: 'var(--tg-theme-text-color)'
            }}
        >
            <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-center"
            >
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: 'spring' }}
                    className="w-20 h-20 mx-auto mb-6 rounded-full bg-green-500/20 flex items-center justify-center"
                >
                    <CheckCircle className="w-10 h-10 text-green-500" />
                </motion.div>
                
                <h1 className="text-2xl font-bold mb-2">
                    {lang === 'ru' ? 'Оплата успешна!' : 'Payment Successful!'}
                </h1>
                
                <p className="text-[var(--tg-theme-hint-color)] mb-4">
                    {lang === 'ru' 
                        ? 'Ваши данные для входа отправлены в чат с ботом.'
                        : 'Your credentials have been sent to the bot chat.'
                    }
                </p>
                
                {orderId && (
                    <p className="text-sm text-[var(--tg-theme-hint-color)]">
                        {lang === 'ru' ? 'Заказ' : 'Order'}: #{orderId.slice(0, 8)}
                    </p>
                )}
            </motion.div>
        </div>
    );
}

