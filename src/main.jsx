import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'

// Pages
import Payment from './pages/Payment'
import Orders from './pages/Orders'
import Success from './pages/Success'

// Create React Query client
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5, // 5 minutes
            retry: 1
        }
    }
})

// Simple home component
function Home() {
    return (
        <div 
            className="min-h-screen flex items-center justify-center p-4"
            style={{
                backgroundColor: 'var(--tg-theme-bg-color, #1a1a2e)',
                color: 'var(--tg-theme-text-color, #ffffff)'
            }}
        >
            <div className="text-center">
                <h1 className="text-3xl font-bold mb-4">🤖 PVNDORA</h1>
                <p className="text-gray-400">AI Marketplace for Premium Subscriptions</p>
            </div>
        </div>
    )
}

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/payment" element={<Payment />} />
                    <Route path="/payment/success" element={<Success />} />
                    <Route path="/payment/cancel" element={<Payment />} />
                    <Route path="/orders" element={<Orders />} />
                </Routes>
            </BrowserRouter>
        </QueryClientProvider>
    </React.StrictMode>
)
