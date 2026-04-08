import { useState } from 'react';
import { client } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import {
  MailIcon, ShirtIcon, SparklesIcon, Loader2Icon,
  ExternalLinkIcon, StarIcon, HeartIcon, TagIcon,
  PackageIcon, PaletteIcon, ArrowLeftIcon, BugIcon,
  CheckCircleIcon, AlertCircleIcon, InfoIcon,
  WrenchIcon, ArrowRightIcon, DatabaseIcon, RefreshCwIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';

interface Product {
  id: number;
  nome: string;
  categoria?: string;
  cor?: string;
  preco?: number;
  imagem_url?: string;
  link_produto?: string;
  tags_estilo?: string;
  colecao?: string;
  tamanho?: string;
  sku?: string;
}

interface Recommendation {
  produto_id: number;
  nome: string;
  motivo: string;
  score: number;
  link_produto?: string;
  imagem_url?: string;
  preco?: number;
  categoria?: string;
  cor?: string;
  combina_com?: string[];
}

interface ClienteData {
  nome: string;
  email: string;
  estilo_resumo?: string;
  tamanho_top?: string;
  tamanho_bottom?: string;
  tamanho_dress?: string;
  cidade?: string;
}

interface DebugInfo {
  email_input?: string;
  email_normalized?: string;
  cliente_found?: boolean;
  pedidos_count?: number;
  itens_pedido_count?: number;
  itens_with_produto_id?: number;
  itens_with_sku_only?: number;
  produtos_by_id?: number;
  produtos_by_sku?: number;
  closet_entries_existing?: number;
  closet_final_count?: number;
  strategy_used?: string;
  messages?: string[];
}

interface CleanupResult {
  clientes_removed: number;
  clientes_kept: number;
  pedidos_linked: number;
  itens_fixed: number;
  email_populated: number;
  duplicates_removed: number;
  closet_synced: number;
  messages: string[];
}

type ViewState = 'login' | 'closet' | 'recommendations';

export default function MeuClosetPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [recsLoading, setRecsLoading] = useState(false);
  const [view, setView] = useState<ViewState>('login');
  const [cliente, setCliente] = useState<ClienteData | null>(null);
  const [closetProducts, setClosetProducts] = useState<Product[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [perfilEstilo, setPerfilEstilo] = useState('');
  const [dicasEstilo, setDicasEstilo] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<CleanupResult | null>(null);
  const { language } = useLanguage();
  const { empresa } = useEmpresa();

  const t = (pt: string, en: string) => language === 'pt' ? pt : en;

  const handleLookup = async () => {
    if (!email.trim()) {
      toast.error(t('Digite seu e-mail', 'Enter your email'));
      return;
    }
    setLoading(true);
    setDebugInfo(null);
    setCleanupResult(null);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/customer-closet/lookup',
        method: 'POST',
        data: { email: email.trim() },
      });
      const data = res.data;
      if (data.debug) {
        setDebugInfo(data.debug);
      }
      if (!data.found) {
        toast.error(t(
          'E-mail não encontrado. Verifique se é o mesmo e-mail usado nas suas compras.',
          'Email not found. Make sure it matches the email used for your purchases.'
        ));
        setShowDebug(true);
        return;
      }
      setCliente(data.cliente);
      setClosetProducts(data.closet_products || []);
      setView('closet');
      const itemCount = data.closet_products?.length || 0;
      toast.success(t(
        `Bem-vinda, ${data.cliente.nome}! ${itemCount} peça(s) encontrada(s).`,
        `Welcome, ${data.cliente.nome}! ${itemCount} item(s) found.`
      ));
    } catch (err: any) {
      console.error('Lookup error:', err);
      const detail = err?.data?.detail || err?.response?.data?.detail || err?.message || 'Erro';
      toast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleGetRecommendations = async () => {
    setRecsLoading(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/customer-closet/recommendations',
        method: 'POST',
        data: { email: email.trim(), limit: 8 },
        options: { timeout: 60000 },
      });
      const data = res.data;
      if (data.debug) {
        setDebugInfo(data.debug);
      }
      setRecommendations(data.recommendations || []);
      setPerfilEstilo(data.perfil_estilo || '');
      setDicasEstilo(data.dicas_estilo || []);
      setView('recommendations');
    } catch (err: any) {
      console.error('Recommendations error:', err);
      const detail = err?.data?.detail || err?.response?.data?.detail || err?.message || 'Erro';
      toast.error(t(
        `Erro ao gerar recomendações: ${detail}`,
        `Error generating recommendations: ${detail}`
      ));
    } finally {
      setRecsLoading(false);
    }
  };

  const handleCleanup = async () => {
    if (!empresa) {
      toast.error(t('Configure uma empresa primeiro', 'Set up a company first'));
      return;
    }
    setCleanupLoading(true);
    setCleanupResult(null);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/import/cleanup-data',
        method: 'POST',
        data: { empresa_id: empresa.id },
      });
      setCleanupResult(res.data);
      toast.success(t('Limpeza concluída!', 'Cleanup complete!'));
    } catch (err: any) {
      console.error('Cleanup error:', err);
      const detail = err?.data?.detail || err?.response?.data?.detail || err?.message || 'Erro';
      toast.error(t(`Erro na limpeza: ${detail}`, `Cleanup error: ${detail}`));
    } finally {
      setCleanupLoading(false);
    }
  };

  const categories = Array.from(new Set(closetProducts.map(p => p.categoria).filter(Boolean)));
  const filteredProducts = selectedCategory
    ? closetProducts.filter(p => p.categoria === selectedCategory)
    : closetProducts;

  const strategyLabels: Record<string, { pt: string; en: string; color: string }> = {
    cliente_id: { pt: 'Vínculo direto (cliente_id)', en: 'Direct link (cliente_id)', color: 'text-green-600' },
    email_cliente: { pt: 'Email no pedido', en: 'Email on order', color: 'text-blue-600' },
    corrupted_nome_match: { pt: 'Dados corrompidos (nome)', en: 'Corrupted data (nome)', color: 'text-amber-600' },
    unlinked_fallback: { pt: 'Fallback (pedidos sem vínculo)', en: 'Fallback (unlinked orders)', color: 'text-orange-600' },
    none: { pt: 'Nenhuma estratégia', en: 'No strategy', color: 'text-red-600' },
  };

  // Enhanced Debug Panel
  const DebugPanel = () => {
    if (!debugInfo && !cleanupResult) return null;
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm text-slate-700 flex items-center gap-2">
            <BugIcon className="h-4 w-4" />
            {t('Diagnóstico Avançado', 'Advanced Diagnostics')}
          </h3>
          <Button variant="ghost" size="sm" onClick={() => setShowDebug(false)} className="text-xs">
            {t('Fechar', 'Close')}
          </Button>
        </div>

        {debugInfo && (
          <>
            {/* Strategy indicator */}
            {debugInfo.strategy_used && (
              <div className="mb-4 p-3 bg-white rounded-lg border border-slate-200">
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                  {t('Estratégia de Busca', 'Lookup Strategy')}
                </p>
                <p className={`text-sm font-bold ${strategyLabels[debugInfo.strategy_used]?.color || 'text-slate-800'}`}>
                  {strategyLabels[debugInfo.strategy_used]?.[language] || debugInfo.strategy_used}
                </p>
              </div>
            )}

            {/* Chain visualization */}
            <div className="mb-4 p-3 bg-white rounded-lg border border-slate-200">
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">
                {t('Cadeia de Dados', 'Data Chain')}
              </p>
              <div className="flex items-center gap-1 flex-wrap text-xs">
                <span className={`px-2 py-1 rounded-full font-medium ${debugInfo.email_normalized ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'}`}>
                  📧 {debugInfo.email_normalized || '-'}
                </span>
                <ArrowRightIcon className="h-3 w-3 text-slate-400 flex-shrink-0" />
                <span className={`px-2 py-1 rounded-full font-medium ${debugInfo.cliente_found ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  👤 {debugInfo.cliente_found ? '✅' : '❌'} {t('Cliente', 'Customer')}
                </span>
                <ArrowRightIcon className="h-3 w-3 text-slate-400 flex-shrink-0" />
                <span className={`px-2 py-1 rounded-full font-medium ${(debugInfo.pedidos_count ?? 0) > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  🛒 {debugInfo.pedidos_count ?? 0} {t('Pedidos', 'Orders')}
                </span>
                <ArrowRightIcon className="h-3 w-3 text-slate-400 flex-shrink-0" />
                <span className={`px-2 py-1 rounded-full font-medium ${(debugInfo.itens_pedido_count ?? 0) > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  📋 {debugInfo.itens_pedido_count ?? 0} {t('Itens', 'Items')}
                </span>
                <ArrowRightIcon className="h-3 w-3 text-slate-400 flex-shrink-0" />
                <span className={`px-2 py-1 rounded-full font-medium ${(debugInfo.closet_final_count ?? 0) > 0 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                  👗 {debugInfo.closet_final_count ?? 0} {t('Peças', 'Items')}
                </span>
              </div>
            </div>

            {/* Detail stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
              <DebugStat label={t('Por ID', 'By ID')} value={String(debugInfo.produtos_by_id ?? 0)} />
              <DebugStat label={t('Por SKU', 'By SKU')} value={String(debugInfo.produtos_by_sku ?? 0)} />
              <DebugStat label={t('Com produto_id', 'With produto_id')} value={String(debugInfo.itens_with_produto_id ?? 0)} />
              <DebugStat label={t('Closet existente', 'Existing closet')} value={String(debugInfo.closet_entries_existing ?? 0)} />
            </div>

            {/* Log messages */}
            {debugInfo.messages && debugInfo.messages.length > 0 && (
              <div className="space-y-1 mb-4">
                <p className="text-xs font-semibold text-slate-600 mb-1">{t('Log:', 'Log:')}</p>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {debugInfo.messages.map((msg, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                      {msg.includes('encontrado') && !msg.includes('Nenhum') ? (
                        <CheckCircleIcon className="h-3 w-3 mt-0.5 text-green-500 flex-shrink-0" />
                      ) : msg.includes('Nenhum') || msg.includes('não encontrad') || msg.includes('nenhum') ? (
                        <AlertCircleIcon className="h-3 w-3 mt-0.5 text-amber-500 flex-shrink-0" />
                      ) : (
                        <InfoIcon className="h-3 w-3 mt-0.5 text-blue-500 flex-shrink-0" />
                      )}
                      {msg}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Cleanup section */}
        {empresa && (
          <div className="border-t border-slate-200 pt-3 mt-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                <WrenchIcon className="h-3 w-3" />
                {t('Ferramentas de Manutenção', 'Maintenance Tools')}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleCleanup}
                disabled={cleanupLoading}
                className="text-xs border-amber-300 text-amber-700 hover:bg-amber-50"
              >
                {cleanupLoading ? (
                  <><Loader2Icon className="h-3 w-3 mr-1 animate-spin" />{t('Limpando...', 'Cleaning...')}</>
                ) : (
                  <><DatabaseIcon className="h-3 w-3 mr-1" />{t('Limpar Dados Corrompidos', 'Clean Corrupted Data')}</>
                )}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleLookup}
                disabled={loading || !email.trim()}
                className="text-xs border-blue-300 text-blue-700 hover:bg-blue-50"
              >
                <RefreshCwIcon className="h-3 w-3 mr-1" />
                {t('Re-buscar', 'Re-search')}
              </Button>
            </div>

            {/* Cleanup results */}
            {cleanupResult && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-xs font-semibold text-green-800 mb-2 flex items-center gap-1">
                  <CheckCircleIcon className="h-3 w-3" />
                  {t('Resultado da Limpeza', 'Cleanup Result')}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2">
                  <div className="text-xs">
                    <span className="text-green-600 font-bold">{cleanupResult.clientes_removed}</span>{' '}
                    <span className="text-green-700">{t('clientes removidos', 'clients removed')}</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-blue-600 font-bold">{cleanupResult.pedidos_linked}</span>{' '}
                    <span className="text-blue-700">{t('pedidos vinculados', 'orders linked')}</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-purple-600 font-bold">{cleanupResult.itens_fixed}</span>{' '}
                    <span className="text-purple-700">{t('itens corrigidos', 'items fixed')}</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-amber-600 font-bold">{cleanupResult.closet_synced ?? 0}</span>{' '}
                    <span className="text-amber-700">{t('closet sincronizado', 'closet synced')}</span>
                  </div>
                </div>
                {cleanupResult.messages.length > 0 && (
                  <div className="space-y-0.5">
                    {cleanupResult.messages.map((msg, i) => (
                      <p key={i} className="text-xs text-green-700">{msg}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const DebugStat = ({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) => (
    <div className="bg-white rounded-lg p-2 border border-slate-100">
      <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
      <p className={`text-sm font-bold ${highlight === true ? 'text-green-600' : highlight === false ? 'text-red-500' : 'text-slate-800'}`}>
        {value}
      </p>
    </div>
  );

  // Login View
  if (view === 'login') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#FAF8F5] to-white">
        <header className="border-b border-[#E8E0D4] bg-white/80 backdrop-blur-lg">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-center">
            <span className="text-xl font-bold tracking-tight" style={{ fontFamily: "'DM Serif Display', serif" }}>
              mood<span className="text-[#A3966A]">·</span>lab
            </span>
            <span className="text-xs font-medium text-[#A3966A] tracking-widest uppercase ml-1" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              .AI
            </span>
          </div>
        </header>

        <div className="flex flex-col items-center justify-center min-h-[80vh] px-4">
          <div className="w-full max-w-md">
            <div className="flex justify-center mb-6">
              <div className="w-20 h-20 rounded-full bg-[#A3966A]/10 flex items-center justify-center">
                <ShirtIcon className="h-10 w-10 text-[#A3966A]" />
              </div>
            </div>

            <h1 className="text-3xl font-bold text-center mb-2" style={{ fontFamily: "'DM Serif Display', serif" }}>
              {t('Meu Closet', 'My Closet')}
            </h1>
            <p className="text-center text-muted-foreground mb-8">
              {t(
                'Digite seu e-mail para acessar suas peças e receber recomendações personalizadas.',
                'Enter your email to access your items and get personalized recommendations.'
              )}
            </p>

            <div className="space-y-4">
              <div className="relative">
                <MailIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  type="email"
                  placeholder={t('seu@email.com', 'your@email.com')}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
                  className="pl-10 h-12 text-base border-[#E8E0D4] focus:border-[#A3966A] focus:ring-[#A3966A]"
                />
              </div>
              <Button
                onClick={handleLookup}
                disabled={loading}
                className="w-full h-12 bg-[#A3966A] hover:bg-[#895D2B] text-white font-semibold text-base"
              >
                {loading ? (
                  <><Loader2Icon className="h-5 w-5 mr-2 animate-spin" />{t('Buscando...', 'Searching...')}</>
                ) : (
                  <>{t('Acessar Meu Closet', 'Access My Closet')}</>
                )}
              </Button>
            </div>

            <p className="text-xs text-center text-muted-foreground mt-6">
              {t(
                'Use o mesmo e-mail cadastrado nas suas compras.',
                'Use the same email registered with your purchases.'
              )}
            </p>

            {/* Debug toggle */}
            <div className="mt-4 text-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDebug(!showDebug)}
                className="text-xs text-muted-foreground"
              >
                <BugIcon className="h-3 w-3 mr-1" />
                {t('Modo diagnóstico', 'Diagnostic mode')}
              </Button>
            </div>

            {showDebug && <DebugPanel />}
          </div>
        </div>
      </div>
    );
  }

  // Closet View
  if (view === 'closet') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#FAF8F5] to-white">
        <header className="border-b border-[#E8E0D4] bg-white/80 backdrop-blur-lg sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xl font-bold tracking-tight" style={{ fontFamily: "'DM Serif Display', serif" }}>
                mood<span className="text-[#A3966A]">·</span>lab
              </span>
              <span className="text-xs font-medium text-[#A3966A] tracking-widest uppercase" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                .AI
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDebug(!showDebug)}
                className="text-xs text-muted-foreground"
              >
                <BugIcon className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => { setView('login'); setCliente(null); setClosetProducts([]); setEmail(''); setDebugInfo(null); setCleanupResult(null); }}
                className="text-muted-foreground"
              >
                {t('Sair', 'Exit')}
              </Button>
            </div>
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Debug Panel */}
          {showDebug && <DebugPanel />}

          {/* Welcome */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
            <div>
              <h1 className="text-3xl font-bold mb-1" style={{ fontFamily: "'DM Serif Display', serif" }}>
                {t('Olá', 'Hello')}, {cliente?.nome?.split(' ')[0]}! 👋
              </h1>
              <p className="text-muted-foreground">
                {closetProducts.length} {closetProducts.length === 1
                  ? t('peça no seu closet', 'item in your closet')
                  : t('peças no seu closet', 'items in your closet')}
              </p>
              {cliente?.estilo_resumo && (
                <Badge variant="outline" className="mt-2 text-[#A3966A] border-[#A3966A]">
                  <PaletteIcon className="h-3 w-3 mr-1" />
                  {cliente.estilo_resumo}
                </Badge>
              )}
            </div>
            <Button
              onClick={handleGetRecommendations}
              disabled={recsLoading}
              className="bg-[#A3966A] hover:bg-[#895D2B] text-white font-semibold"
            >
              {recsLoading ? (
                <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" />{t('Gerando...', 'Generating...')}</>
              ) : (
                <><SparklesIcon className="h-4 w-4 mr-2" />{t('Ver recomendações para mim', 'See recommendations for me')}</>
              )}
            </Button>
          </div>

          {/* Category Tabs */}
          {categories.length > 0 && (
            <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
              <Button
                variant={selectedCategory === null ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(null)}
                className={selectedCategory === null ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white' : ''}
              >
                {t('Todas', 'All')} ({closetProducts.length})
              </Button>
              {categories.map((cat) => {
                const count = closetProducts.filter(p => p.categoria === cat).length;
                return (
                  <Button
                    key={cat}
                    variant={selectedCategory === cat ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedCategory(cat)}
                    className={`capitalize flex-shrink-0 ${
                      selectedCategory === cat ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white' : ''
                    }`}
                  >
                    {cat} ({count})
                  </Button>
                );
              })}
            </div>
          )}

          {/* Products Grid */}
          {closetProducts.length === 0 ? (
            <div className="text-center py-16">
              <PackageIcon className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">
                {t('Nenhuma peça encontrada no closet', 'No items found in closet')}
              </h3>
              <p className="text-muted-foreground mb-6">
                {t(
                  'Seus itens comprados aparecerão aqui automaticamente. Mas você ainda pode ver recomendações!',
                  'Your purchased items will appear here automatically. But you can still see recommendations!'
                )}
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button
                  onClick={handleGetRecommendations}
                  disabled={recsLoading}
                  className="bg-[#A3966A] hover:bg-[#895D2B] text-white font-semibold"
                >
                  {recsLoading ? (
                    <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" />{t('Gerando...', 'Generating...')}</>
                  ) : (
                    <><SparklesIcon className="h-4 w-4 mr-2" />{t('Ver recomendações do catálogo', 'See catalog recommendations')}</>
                  )}
                </Button>
                {empresa && (
                  <Button
                    variant="outline"
                    onClick={() => { setShowDebug(true); handleCleanup(); }}
                    disabled={cleanupLoading}
                    className="border-amber-300 text-amber-700 hover:bg-amber-50"
                  >
                    {cleanupLoading ? (
                      <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" />{t('Corrigindo...', 'Fixing...')}</>
                    ) : (
                      <><WrenchIcon className="h-4 w-4 mr-2" />{t('Corrigir dados e tentar novamente', 'Fix data and retry')}</>
                    )}
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {filteredProducts.map((product) => (
                <Card
                  key={product.id}
                  className="overflow-hidden group hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5"
                >
                  <div className="aspect-square overflow-hidden bg-[#F5F0EB]">
                    {product.imagem_url ? (
                      <img
                        src={product.imagem_url}
                        alt={product.nome}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <ShirtIcon className="h-12 w-12 text-[#D4C9B8]" />
                      </div>
                    )}
                  </div>
                  <CardContent className="p-3">
                    <h4 className="font-medium text-sm line-clamp-2 mb-1">{product.nome}</h4>
                    <div className="flex flex-wrap items-center gap-1 mt-1">
                      {product.categoria && (
                        <Badge variant="outline" className="text-xs capitalize">{product.categoria}</Badge>
                      )}
                      {product.cor && (
                        <Badge variant="secondary" className="text-xs">{product.cor}</Badge>
                      )}
                    </div>
                    {product.preco != null && (
                      <p className="text-sm font-semibold text-[#A3966A] mt-2">
                        R$ {Number(product.preco).toFixed(2)}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Recommendations View
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#FAF8F5] to-white">
      <header className="border-b border-[#E8E0D4] bg-white/80 backdrop-blur-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold tracking-tight" style={{ fontFamily: "'DM Serif Display', serif" }}>
              mood<span className="text-[#A3966A]">·</span>lab
            </span>
            <span className="text-xs font-medium text-[#A3966A] tracking-widest uppercase" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              .AI
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDebug(!showDebug)}
              className="text-xs text-muted-foreground"
            >
              <BugIcon className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setView('closet')}
              className="text-muted-foreground"
            >
              <ArrowLeftIcon className="h-4 w-4 mr-1" />
              {t('Voltar ao Closet', 'Back to Closet')}
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Debug Panel */}
        {showDebug && <DebugPanel />}

        {/* Style Profile */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <SparklesIcon className="h-6 w-6 text-[#A3966A]" />
            <h1 className="text-3xl font-bold" style={{ fontFamily: "'DM Serif Display', serif" }}>
              {t('Recomendações para você', 'Recommendations for you')}
            </h1>
          </div>
          {perfilEstilo && (
            <p className="text-muted-foreground max-w-2xl">{perfilEstilo}</p>
          )}
        </div>

        {/* Style Tips */}
        {dicasEstilo.length > 0 && (
          <div className="bg-[#A3966A]/5 border border-[#A3966A]/20 rounded-xl p-5 mb-8">
            <h3 className="font-semibold text-[#895D2B] mb-3 flex items-center gap-2">
              <HeartIcon className="h-4 w-4" />
              {t('Dicas de Estilo', 'Style Tips')}
            </h3>
            <ul className="space-y-2">
              {dicasEstilo.map((dica, i) => (
                <li key={i} className="text-sm text-[#6B5D4A] flex items-start gap-2">
                  <StarIcon className="h-3.5 w-3.5 mt-0.5 text-[#A3966A] flex-shrink-0" />
                  {dica}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations Grid */}
        {recommendations.length === 0 ? (
          <div className="text-center py-16">
            <SparklesIcon className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">
              {t('Nenhuma recomendação disponível', 'No recommendations available')}
            </h3>
            <p className="text-muted-foreground">
              {t(
                'O catálogo da marca ainda não possui produtos suficientes para gerar recomendações.',
                'The brand catalog does not have enough products to generate recommendations yet.'
              )}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {recommendations.map((rec, idx) => (
              <Card
                key={idx}
                className="overflow-hidden group hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border-[#E8E0D4]"
              >
                <div className="aspect-square overflow-hidden bg-[#F5F0EB] relative">
                  {rec.imagem_url ? (
                    <img
                      src={rec.imagem_url}
                      alt={rec.nome}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <ShirtIcon className="h-12 w-12 text-[#D4C9B8]" />
                    </div>
                  )}
                  <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm rounded-full px-2 py-1 flex items-center gap-1">
                    <StarIcon className="h-3 w-3 text-[#A3966A] fill-[#A3966A]" />
                    <span className="text-xs font-semibold">{Math.round(rec.score * 100)}%</span>
                  </div>
                </div>
                <CardContent className="p-4">
                  <h4 className="font-semibold text-sm line-clamp-2 mb-2">{rec.nome}</h4>
                  <p className="text-xs text-muted-foreground line-clamp-3 mb-3">{rec.motivo}</p>

                  <div className="flex flex-wrap items-center gap-1 mb-3">
                    {rec.categoria && (
                      <Badge variant="outline" className="text-xs capitalize">{rec.categoria}</Badge>
                    )}
                    {rec.cor && (
                      <Badge variant="secondary" className="text-xs">{rec.cor}</Badge>
                    )}
                  </div>

                  {rec.combina_com && rec.combina_com.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                        <TagIcon className="h-3 w-3" />
                        {t('Combina com:', 'Pairs with:')}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {rec.combina_com.map((item, i) => (
                          <Badge key={i} variant="outline" className="text-xs bg-[#A3966A]/5 border-[#A3966A]/20">
                            {item}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between mt-auto pt-2 border-t border-[#E8E0D4]">
                    {rec.preco != null && (
                      <span className="font-bold text-[#A3966A]">R$ {Number(rec.preco).toFixed(2)}</span>
                    )}
                    {rec.link_produto ? (
                      <a
                        href={rec.link_produto}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-semibold text-[#A3966A] hover:text-[#895D2B] transition-colors"
                      >
                        {t('Ver produto', 'View product')}
                        <ExternalLinkIcon className="h-3 w-3" />
                      </a>
                    ) : (
                      !rec.preco && <span className="text-xs text-muted-foreground">{t('Em breve', 'Coming soon')}</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <div className="text-center mt-12">
          <Button
            variant="outline"
            onClick={() => setView('closet')}
            className="border-[#A3966A] text-[#A3966A] hover:bg-[#A3966A]/10"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            {t('Voltar ao Meu Closet', 'Back to My Closet')}
          </Button>
        </div>
      </div>
    </div>
  );
}