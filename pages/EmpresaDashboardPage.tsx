import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  UsersIcon, PackageIcon, ShoppingCartIcon, ShirtIcon,
  BarChart3Icon, AlertTriangleIcon, PackageXIcon, TrendingDownIcon,
  HeartPulseIcon, DatabaseIcon, WrenchIcon, Loader2Icon,
  CheckCircleIcon, AlertCircleIcon, LinkIcon, RefreshCwIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

interface StockSummary {
  total_produtos: number;
  em_estoque: number;
  fora_estoque: number;
  estoque_baixo: number;
  sem_info_estoque: number;
  produtos_esgotados: { id: number; sku: string; nome: string; estoque: number; preco: number }[];
  produtos_estoque_baixo: { id: number; sku: string; nome: string; estoque: number; preco: number }[];
}

interface DataHealth {
  total_clientes: number;
  total_produtos: number;
  total_pedidos: number;
  total_itens_pedido: number;
  total_closet: number;
  corrupted_clientes: number;
  unlinked_pedidos: number;
  orphan_itens: number;
  health_score: number;
}

export default function EmpresaDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ clientes: 0, produtos: 0, pedidos: 0, closet: 0 });
  const [recentOrders, setRecentOrders] = useState<any[]>([]);
  const [stockSummary, setStockSummary] = useState<StockSummary | null>(null);
  const [dataHealth, setDataHealth] = useState<DataHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [cleanupLoading, setCleanupLoading] = useState(false);
  const { t, language } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();

  useEffect(() => {
    if (empresa) fetchData();
    else setLoading(false);
  }, [empresa]);

  const fetchData = async () => {
    try {
      const [clientesRes, produtosRes, pedidosRes, closetRes] = await Promise.all([
        client.entities.clientes.query({ query: { empresa_id: empresa!.id }, limit: 1 }),
        client.entities.produtos_empresa.query({ query: { empresa_id: empresa!.id }, limit: 1 }),
        client.entities.pedidos.query({ query: { empresa_id: empresa!.id }, limit: 5, sort: '-data_pedido' }),
        client.entities.closet_cliente.query({ query: { empresa_id: empresa!.id }, limit: 1 }),
      ]);

      setStats({
        clientes: clientesRes.data?.total || 0,
        produtos: produtosRes.data?.total || 0,
        pedidos: pedidosRes.data?.total || 0,
        closet: closetRes.data?.total || 0,
      });
      setRecentOrders(pedidosRes.data?.items || []);

      // Fetch stock summary
      try {
        const stockRes = await client.apiCall.invoke({
          url: '/api/v1/stock/summary',
          method: 'GET',
          data: { empresa_id: empresa!.id },
        });
        setStockSummary(stockRes.data);
      } catch (err) { console.error('Stock summary error:', err); }

      // Fetch data health
      await fetchHealth();
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const fetchHealth = async () => {
    if (!empresa) return;
    setHealthLoading(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/import/data-health',
        method: 'POST',
        data: { empresa_id: empresa.id },
      });
      setDataHealth(res.data);
    } catch (err) {
      console.error('Health check error:', err);
    } finally {
      setHealthLoading(false);
    }
  };

  const handleCleanup = async () => {
    if (!empresa) return;
    setCleanupLoading(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/import/cleanup-data',
        method: 'POST',
        data: { empresa_id: empresa.id },
      });
      const data = res.data;
      toast.success(
        language === 'pt'
          ? `Limpeza concluída! ${data.clientes_removed} clientes removidos, ${data.pedidos_linked} pedidos vinculados, ${data.closet_synced ?? 0} closet sincronizado.`
          : `Cleanup complete! ${data.clientes_removed} clients removed, ${data.pedidos_linked} orders linked, ${data.closet_synced ?? 0} closet synced.`
      );
      // Refresh data
      await fetchData();
    } catch (err: any) {
      const detail = err?.data?.detail || err?.response?.data?.detail || err?.message || 'Error';
      toast.error(detail);
    } finally {
      setCleanupLoading(false);
    }
  };

  const getHealthColor = (score: number) => {
    if (score >= 75) return 'text-green-600';
    if (score >= 50) return 'text-amber-600';
    return 'text-red-600';
  };

  const getHealthBg = (score: number) => {
    if (score >= 75) return 'bg-green-50 border-green-200';
    if (score >= 50) return 'bg-amber-50 border-amber-200';
    return 'bg-red-50 border-red-200';
  };

  if (!empresa) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <BarChart3Icon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('import.noEmpresa')}</h2>
          <Button onClick={() => navigate('/empresa')} className="bg-[#A3966A] hover:bg-[#895D2B] text-white mt-4">{t('empresa.title')}</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('edash.title')}</h1>
            <p className="text-muted-foreground">{t('edash.subtitle')}</p>
          </div>
          <Badge className="bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10">{empresa.nome_empresa}</Badge>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => navigate('/clientes')}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">{t('edash.totalClientes')}</span>
                <UsersIcon className="h-5 w-5 text-[#A3966A]" />
              </div>
              <p className="text-3xl font-bold text-foreground">{loading ? '-' : stats.clientes}</p>
              {dataHealth && dataHealth.corrupted_clientes > 0 && (
                <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                  <AlertTriangleIcon className="h-3 w-3" />
                  {dataHealth.corrupted_clientes} {language === 'pt' ? 'corrompido(s)' : 'corrupted'}
                </p>
              )}
            </CardContent>
          </Card>
          <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={() => navigate('/catalogo')}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">{t('edash.totalProdutos')}</span>
                <PackageIcon className="h-5 w-5 text-[#895D2B]" />
              </div>
              <p className="text-3xl font-bold text-foreground">{loading ? '-' : stats.produtos}</p>
              {stockSummary && stockSummary.fora_estoque > 0 && (
                <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                  <PackageXIcon className="h-3 w-3" />
                  {stockSummary.fora_estoque} {language === 'pt' ? 'esgotado(s)' : 'out of stock'}
                </p>
              )}
            </CardContent>
          </Card>
          <Card className="hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">{t('edash.totalPedidos')}</span>
                <ShoppingCartIcon className="h-5 w-5 text-[#90533C]" />
              </div>
              <p className="text-3xl font-bold text-foreground">{loading ? '-' : stats.pedidos}</p>
              {dataHealth && dataHealth.unlinked_pedidos > 0 && (
                <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                  <LinkIcon className="h-3 w-3" />
                  {dataHealth.unlinked_pedidos} {language === 'pt' ? 'sem vínculo' : 'unlinked'}
                </p>
              )}
            </CardContent>
          </Card>
          <Card className="hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">{t('edash.closetEntries')}</span>
                <ShirtIcon className="h-5 w-5 text-[#482D1E]" />
              </div>
              <p className="text-3xl font-bold text-foreground">{loading ? '-' : stats.closet}</p>
            </CardContent>
          </Card>
        </div>

        {/* Data Health Card */}
        {dataHealth && (
          <Card className={`mb-8 border ${getHealthBg(dataHealth.health_score)}`}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <HeartPulseIcon className="h-5 w-5" />
                  {language === 'pt' ? 'Saúde dos Dados' : 'Data Health'}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchHealth}
                    disabled={healthLoading}
                    className="text-xs"
                  >
                    {healthLoading ? (
                      <Loader2Icon className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCwIcon className="h-3 w-3" />
                    )}
                  </Button>
                  <div className={`text-3xl font-bold ${getHealthColor(dataHealth.health_score)}`}>
                    {dataHealth.health_score}%
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                <HealthMetric
                  label={language === 'pt' ? 'Clientes corrompidos' : 'Corrupted clients'}
                  value={dataHealth.corrupted_clientes}
                  isGood={dataHealth.corrupted_clientes === 0}
                />
                <HealthMetric
                  label={language === 'pt' ? 'Pedidos sem vínculo' : 'Unlinked orders'}
                  value={dataHealth.unlinked_pedidos}
                  isGood={dataHealth.unlinked_pedidos === 0}
                />
                <HealthMetric
                  label={language === 'pt' ? 'Itens órfãos' : 'Orphan items'}
                  value={dataHealth.orphan_itens}
                  isGood={dataHealth.orphan_itens === 0}
                />
                <HealthMetric
                  label={language === 'pt' ? 'Entradas closet' : 'Closet entries'}
                  value={dataHealth.total_closet}
                  isGood={dataHealth.total_closet > 0 || dataHealth.total_pedidos === 0}
                />
              </div>

              {/* Show cleanup button if there are issues */}
              {dataHealth.health_score < 100 && (
                <div className="flex items-center gap-3 p-3 bg-white/80 rounded-lg border border-slate-200">
                  <DatabaseIcon className="h-5 w-5 text-amber-600 flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      {language === 'pt'
                        ? 'Foram detectados problemas nos dados. Execute a limpeza para corrigir automaticamente.'
                        : 'Data issues detected. Run cleanup to fix automatically.'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {language === 'pt'
                        ? 'Remove duplicatas, vincula pedidos a clientes, corrige referências e sincroniza o closet.'
                        : 'Removes duplicates, links orders to clients, fixes references and syncs closet.'}
                    </p>
                  </div>
                  <Button
                    onClick={handleCleanup}
                    disabled={cleanupLoading}
                    size="sm"
                    className="bg-amber-600 hover:bg-amber-700 text-white flex-shrink-0"
                  >
                    {cleanupLoading ? (
                      <><Loader2Icon className="h-4 w-4 mr-1 animate-spin" />{language === 'pt' ? 'Limpando...' : 'Cleaning...'}</>
                    ) : (
                      <><WrenchIcon className="h-4 w-4 mr-1" />{language === 'pt' ? 'Executar Limpeza' : 'Run Cleanup'}</>
                    )}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Stock Alerts */}
        {stockSummary && (stockSummary.fora_estoque > 0 || stockSummary.estoque_baixo > 0) && (
          <Card className="mb-8 border-amber-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangleIcon className="h-5 w-5 text-amber-600" />
                {language === 'pt' ? 'Alertas de Estoque' : 'Stock Alerts'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                  <PackageIcon className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="text-2xl font-bold text-green-700">{stockSummary.em_estoque}</p>
                    <p className="text-xs text-green-600">{language === 'pt' ? 'Em estoque' : 'In stock'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-amber-50 rounded-lg cursor-pointer" onClick={() => navigate('/catalogo')}>
                  <TrendingDownIcon className="h-5 w-5 text-amber-600" />
                  <div>
                    <p className="text-2xl font-bold text-amber-700">{stockSummary.estoque_baixo}</p>
                    <p className="text-xs text-amber-600">{language === 'pt' ? 'Estoque baixo (≤5)' : 'Low stock (≤5)'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-red-50 rounded-lg cursor-pointer" onClick={() => navigate('/catalogo')}>
                  <PackageXIcon className="h-5 w-5 text-red-600" />
                  <div>
                    <p className="text-2xl font-bold text-red-700">{stockSummary.fora_estoque}</p>
                    <p className="text-xs text-red-600">{language === 'pt' ? 'Esgotado' : 'Out of stock'}</p>
                  </div>
                </div>
              </div>

              {/* Out of stock products list */}
              {stockSummary.produtos_esgotados.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-1">
                    <PackageXIcon className="h-4 w-4" />
                    {language === 'pt' ? 'Produtos Esgotados' : 'Out of Stock Products'}
                  </h4>
                  <div className="space-y-1">
                    {stockSummary.produtos_esgotados.slice(0, 5).map((p) => (
                      <div key={p.id} className="flex items-center justify-between p-2 bg-red-50/50 rounded text-sm">
                        <div>
                          <span className="font-medium">{p.nome}</span>
                          <span className="text-muted-foreground ml-2 text-xs">({p.sku})</span>
                        </div>
                        <span className="text-red-600 font-medium">{p.preco ? `R$ ${p.preco.toFixed(2)}` : '-'}</span>
                      </div>
                    ))}
                    {stockSummary.produtos_esgotados.length > 5 && (
                      <Button variant="ghost" size="sm" onClick={() => navigate('/catalogo')} className="text-red-600 text-xs">
                        +{stockSummary.produtos_esgotados.length - 5} {language === 'pt' ? 'mais' : 'more'}...
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {/* Low stock products list */}
              {stockSummary.produtos_estoque_baixo.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-amber-700 mb-2 flex items-center gap-1">
                    <TrendingDownIcon className="h-4 w-4" />
                    {language === 'pt' ? 'Estoque Baixo' : 'Low Stock'}
                  </h4>
                  <div className="space-y-1">
                    {stockSummary.produtos_estoque_baixo.slice(0, 5).map((p) => (
                      <div key={p.id} className="flex items-center justify-between p-2 bg-amber-50/50 rounded text-sm">
                        <div>
                          <span className="font-medium">{p.nome}</span>
                          <span className="text-muted-foreground ml-2 text-xs">({p.sku})</span>
                        </div>
                        <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 text-xs">{language === 'pt' ? `${p.estoque} un.` : `${p.estoque} units`}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Recent Orders */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShoppingCartIcon className="h-5 w-5 text-[#A3966A]" />
              {t('edash.recentOrders')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentOrders.length > 0 ? (
              <div className="space-y-3">
                {recentOrders.map((order: any) => (
                  <div key={order.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div>
                      <span className="text-sm font-medium">#{order.numero_pedido}</span>
                      <p className="text-xs text-muted-foreground">
                        {order.data_pedido ? new Date(order.data_pedido).toLocaleDateString() : '-'}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold">{order.valor_total ? `R$ ${order.valor_total.toFixed(2)}` : '-'}</span>
                      <Badge variant="secondary" className="capitalize">{order.status || 'pending'}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">{t('edash.noData')}</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function HealthMetric({ label, value, isGood }: { label: string; value: number; isGood: boolean }) {
  return (
    <div className="flex items-center gap-2 p-3 bg-white/80 rounded-lg border border-slate-100">
      {isGood ? (
        <CheckCircleIcon className="h-4 w-4 text-green-500 flex-shrink-0" />
      ) : (
        <AlertCircleIcon className="h-4 w-4 text-amber-500 flex-shrink-0" />
      )}
      <div>
        <p className={`text-lg font-bold ${isGood ? 'text-green-700' : 'text-amber-700'}`}>{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}