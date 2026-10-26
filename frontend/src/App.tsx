import { ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AuthProvider, useAuth } from './hooks/auth';
import Login from './pages/Login';
import FarmDashboard from './pages/farmer/FarmDashboard';
import Analytics from './pages/farmer/Analytics';
import Control from './pages/farmer/Control';
import Crop from './pages/farmer/Crop';
import Alerts from './pages/farmer/Alerts';
import AdminDashboard from './pages/admin/AdminDashboard';
import Users from './pages/admin/Users';
import Equipment from './pages/admin/Equipment';
import Standards from './pages/admin/Standards';
import Logs from './pages/admin/Logs';
import Weather from './pages/admin/Weather';

function Guard({ children, admin }: { children: ReactNode; admin?: boolean }) {
  const { me, loading } = useAuth();
  if (loading) return <div className="p-8 text-slate-500">불러오는 중…</div>;
  if (!me) return <Navigate to="/login" replace />;
  // 화면 차단은 편의 기능일 뿐이며, 권한 검사는 백엔드 API가 다시 한다
  if (admin && me.role !== 'ADMIN') return <Navigate to="/farm" replace />;
  return <Layout>{children}</Layout>;
}

function Home() {
  const { me, loading } = useAuth();
  if (loading) return null;
  if (!me) return <Navigate to="/login" replace />;
  return <Navigate to={me.role === 'ADMIN' ? '/admin' : '/farm'} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/farm" element={<Guard><FarmDashboard /></Guard>} />
          <Route path="/farm/analytics" element={<Guard><Analytics /></Guard>} />
          <Route path="/farm/control" element={<Guard><Control /></Guard>} />
          <Route path="/farm/crop" element={<Guard><Crop /></Guard>} />
          <Route path="/farm/alerts" element={<Guard><Alerts /></Guard>} />
          <Route path="/admin" element={<Guard admin><AdminDashboard /></Guard>} />
          <Route path="/admin/users" element={<Guard admin><Users /></Guard>} />
          <Route path="/admin/equipment" element={<Guard admin><Equipment /></Guard>} />
          <Route path="/admin/standards" element={<Guard admin><Standards /></Guard>} />
          <Route path="/admin/logs" element={<Guard admin><Logs /></Guard>} />
          <Route path="/admin/weather" element={<Guard admin><Weather /></Guard>} />
          <Route path="*" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
