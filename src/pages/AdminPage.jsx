import React, { useState, useEffect } from 'react';
import { Loader2, Plus, Package, Users, AlertCircle } from 'lucide-react';

const AdminPage = () => {
    const [activeTab, setActiveTab] = useState('products'); // products, stock, stats
    const [isAdmin, setIsAdmin] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // In real app, verify initData with backend
        const checkAdmin = async () => {
            // Mock check
            const initData = window.Telegram?.WebApp?.initDataUnsafe;
            // For demo, we just allow it or check a specific ID if needed
            // setIsAdmin(initData?.user?.id === YOUR_ADMIN_ID);
            setIsAdmin(true); // Allow for now for development
            setLoading(false);
        };
        checkAdmin();
    }, []);

    if (loading) return <div className="min-h-screen flex items-center justify-center bg-background"><Loader2 className="animate-spin text-primary" /></div>;

    if (!isAdmin) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-background p-6 text-center">
                <AlertCircle className="w-12 h-12 text-error mb-4" />
                <h1 className="text-xl font-bold">Доступ запрещен</h1>
                <p className="text-gray-400">Эта страница только для администраторов.</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-background text-white pb-20">
            <div className="p-6">
                <h1 className="text-2xl font-bold mb-6">Админ-панель</h1>

                {/* Stats Overview */}
                <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="bg-surface p-4 rounded-xl border border-white/5">
                        <div className="text-gray-400 text-xs mb-1">Продажи сегодня</div>
                        <div className="text-2xl font-bold text-success">12 500 ₽</div>
                    </div>
                    <div className="bg-surface p-4 rounded-xl border border-white/5">
                        export default AdminPage;
