import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LanguageProvider } from './contexts/LanguageContext';
import { EmpresaProvider } from './contexts/EmpresaContext';
import Index from './pages/Index';
import AuthCallback from './pages/AuthCallback';
import AuthError from './pages/AuthError';
import NotFound from './pages/NotFound';
import ShopPage from './pages/ShopPage';
import WardrobePage from './pages/WardrobePage';
import StylistPage from './pages/StylistPage';
import DashboardPage from './pages/DashboardPage';
import EmpresaSetupPage from './pages/EmpresaSetupPage';
import IntegrationsPage from './pages/IntegrationsPage';
import CatalogoPage from './pages/CatalogoPage';
import ClientesPage from './pages/ClientesPage';
import EmpresaDashboardPage from './pages/EmpresaDashboardPage';
import BrandSettingsPage from './pages/BrandSettingsPage';
import CuratedLooksPage from './pages/CuratedLooksPage';
import BrandRulesPage from './pages/BrandRulesPage';
import AILearningPage from './pages/AILearningPage';
import MeuClosetPage from './pages/MeuClosetPage';

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <LanguageProvider>
        <EmpresaProvider>
          <Toaster />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Index />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              <Route path="/auth/error" element={<AuthError />} />
              <Route path="/shop" element={<ShopPage />} />
              <Route path="/wardrobe" element={<WardrobePage />} />
              <Route path="/stylist" element={<StylistPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/empresa" element={<EmpresaSetupPage />} />
              <Route path="/integrations" element={<IntegrationsPage />} />
              <Route path="/import" element={<Navigate to="/integrations" replace />} />
              <Route path="/catalogo" element={<CatalogoPage />} />
              <Route path="/clientes" element={<ClientesPage />} />
              <Route path="/empresa-dashboard" element={<EmpresaDashboardPage />} />
              <Route path="/brand-settings" element={<BrandSettingsPage />} />
              <Route path="/curated-looks" element={<CuratedLooksPage />} />
              <Route path="/brand-rules" element={<BrandRulesPage />} />
              <Route path="/ai-learning" element={<AILearningPage />} />
              <Route path="/meu-closet" element={<MeuClosetPage />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </EmpresaProvider>
      </LanguageProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;