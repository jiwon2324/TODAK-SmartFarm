import { ReactNode } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AuthProvider, homeOf, useAuth } from './hooks/auth';
import Login from './pages/auth/Login';
import Demo from './pages/auth/Demo';
import Signup from './pages/auth/Signup';
import Forgot from './pages/auth/Forgot';
import Legal from './pages/auth/Legal';
import PasswordRequired from './pages/auth/PasswordRequired';
import Account from './pages/Account';
import FarmDashboard from './pages/farmer/FarmDashboard';
import Graph from './pages/farmer/Graph';
import Control from './pages/farmer/Control';
import History from './pages/farmer/History';
import FarmStandards from './pages/farmer/Standards';
import Growth from './pages/farmer/Growth';
import Harvest from './pages/farmer/Harvest';
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
  if (me.mustChangePassword) return <Navigate to="/account/password" replace />;
  // 화면 차단은 편의 기능일 뿐이며, 권한 검사는 백엔드 API가 다시 한다
  if (admin && me.role !== 'ADMIN') return <Navigate to="/farm" replace state={{ denied: true }} />;
  return <Layout>{children}</Layout>;
}

function Home() {
  const { me, loading } = useAuth();
  if (loading) return null;
  if (!me) return <Navigate to="/login" replace />;
  return <Navigate to={homeOf(me)} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/forgot" element={<Forgot />} />
          <Route path="/terms" element={<Legal kind="terms" />} />
          <Route path="/privacy" element={<Legal kind="privacy" />} />
          <Route path="/account/password" element={<PasswordRequired />} />
          <Route path="/account" element={<Guard><Account /></Guard>} />
          <Route path="/farm" element={<Guard><FarmDashboard /></Guard>} />
          <Route path="/farm/graph" element={<Guard><Graph /></Guard>} />
          <Route path="/farm/control" element={<Guard><Control /></Guard>} />
          <Route path="/farm/history" element={<Guard><History /></Guard>} />
          <Route path="/farm/standards" element={<Guard><FarmStandards /></Guard>} />
          <Route path="/farm/growth" element={<Guard><Growth /></Guard>} />
          <Route path="/farm/harvest" element={<Guard><Harvest /></Guard>} />
          <Route path="/farm/analytics" element={<Navigate to="/farm/graph" replace />} />
          <Route path="/farm/crop" element={<Navigate to="/farm/growth" replace />} />
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
