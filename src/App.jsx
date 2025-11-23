import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import PaymentPage from './pages/PaymentPage';
import AdminPage from './pages/AdminPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/pay" element={<PaymentPage />} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="*" element={<Navigate to="/pay" replace />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
