import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import {
  PackageIcon, SearchIcon, FilterIcon, AlertTriangleIcon,
  Loader2Icon, RefreshCwIcon, ExternalLinkIcon, XCircleIcon,
  PackageXIcon, TrendingDownIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

interface Produto {
  id: number;
  sku: string;
  nome: string;
  categoria: string;
  subcategoria: string;
  colecao: string;
  cor: string;
  modelagem: string;
  tamanho: string;
  preco: number;
  estoque: number;
  imagem_url: string;
  link_produto: string;
  ocasiao: string;
  tags_estilo: string;
  ativo: boolean;
}

interface StockSummary {
  total_produtos: number;
  em_estoque: number;
  fora_estoque: number;
  estoque_baixo: number;
  sem_info_estoque: number;
  produtos_esgotados: { id: number; sku: string; nome: string; estoque: number; preco: number }[];
  produtos_estoque_baixo: { id: number; sku: string; nome: string; estoque: number; preco: number }[];
}

type StockFilter = 'all' | 'in_stock' | 'low_stock' | 'out_of_stock';

export default function CatalogoPage() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterCat, setFilterCat] = useState('all');
  const [stockFilter, setStockFilter] = useState<StockFilter>('all');
  const [stockSummary, setStockSummary] = useState<StockSummary | null>(null);
  const [fetchingPrice, setFetchingPrice] = useState<number | null>(null);
  const [bulkFetching, setBulkFetching] = useState(false);
  const [processingStock, setProcessingStock] = useState(false);
  const { t, language } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();

  useEffect(() => {
    if (empresa) {
      fetchProdutos();
      fetchStockSummary();
    } else {
      setLoading(false);
    }
  }, [empresa]);

  const fetchProdutos = async () => {
    try {
      const res = await client.entities.produtos_empresa.query({
        query: { empresa_id: empresa!.id },
        limit: 200,
        sort: '-id',
      });
      setProdutos(res.data?.items || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const fetchStockSummary = async () => {
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/stock/summary',
        method: 'GET',
        data: { empresa_id: empresa!.id },
      });
      setStockSummary(res.data);
    } catch (err) { console.error(err); }
  };

  const handleFetchPrice = async (produto: Produto) => {
    if (!produto.link_produto) {
      toast.error(language === 'pt' ? 'Produto sem link cadastrado' : 'Product has no URL');
      return;
    }
    setFetchingPrice(produto.id);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/price/fetch-from-url',
        method: 'POST',
        data: { produto_id: produto.id, empresa_id: empresa!.id },
      });
      const data = res.data;
      if (data.updated) {
        toast.success(
          language === 'pt'
            ? `Preço atualizado: R$ ${data.old_price?.toFixed(2)} → R$ ${data.new_price?.toFixed(2)} (${data.source})`
            : `Price updated: R$ ${data.old_price?.toFixed(2)} → R$ ${data.new_price?.toFixed(2)} (${data.source})`
        );
        setProdutos((prev) => prev.map((p) => p.id === produto.id ? { ...p, preco: data.new_price } : p));
      } else if (data.new_price !== null) {
        toast.info(language === 'pt' ? `Preço atual já está correto: R$ ${data.new_price?.toFixed(2)}` : `Price is already correct: R$ ${data.new_price?.toFixed(2)}`);
      } else {
        toast.warning(language === 'pt' ? `Não foi possível extrair o preço: ${data.source}` : `Could not extract price: ${data.source}`);
      }
    } catch (err) {
      console.error(err);
      toast.error(language === 'pt' ? 'Erro ao buscar preço' : 'Error fetching price');
    } finally {
      setFetchingPrice(null);
    }
  };

  const handleBulkFetchPrices = async () => {
    setBulkFetching(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/price/bulk-fetch',
        method: 'POST',
        data: { empresa_id: empresa!.id },
      });
      const data = res.data;
      toast.success(
        language === 'pt'
          ? `${data.updated} preço(s) atualizado(s) de ${data.total} produto(s) com link`
          : `${data.updated} price(s) updated from ${data.total} product(s) with URL`
      );
      if (data.updated > 0) fetchProdutos();
    } catch (err) {
      console.error(err);
      toast.error(language === 'pt' ? 'Erro na atualização em lote' : 'Bulk update error');
    } finally {
      setBulkFetching(false);
    }
  };

  const handleProcessOrderStock = async () => {
    setProcessingStock(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/stock/process-all-orders',
        method: 'POST',
        data: { empresa_id: empresa!.id },
      });
      const data = res.data;
      toast.success(
        language === 'pt'
          ? `${data.processed_orders} pedido(s) processado(s), ${data.total_deductions} baixa(s) no estoque`
          : `${data.processed_orders} order(s) processed, ${data.total_deductions} stock deduction(s)`
      );
      if (data.total_deductions > 0) {
        fetchProdutos();
        fetchStockSummary();
      }
    } catch (err) {
      console.error(err);
      toast.error(language === 'pt' ? 'Erro ao processar estoque' : 'Stock processing error');
    } finally {
      setProcessingStock(false);
    }
  };

  const categories = ['all', ...Array.from(new Set(produtos.map((p) => p.categoria).filter(Boolean)))];

  const filtered = produtos
    .filter((p) => filterCat === 'all' || p.categoria === filterCat)
    .filter((p) => !search || p.nome?.toLowerCase().includes(search.toLowerCase()) || p.sku?.toLowerCase().includes(search.toLowerCase()))
    .filter((p) => {
      if (stockFilter === 'all') return true;
      if (stockFilter === 'in_stock') return p.estoque === null || p.estoque === undefined || p.estoque > 5;
      if (stockFilter === 'low_stock') return p.estoque !== null && p.estoque !== undefined && p.estoque > 0 && p.estoque <= 5;
      if (stockFilter === 'out_of_stock') return p.estoque !== null && p.estoque !== undefined && p.estoque <= 0;
      return true;
    });

  const getStockBadge = (p: Produto) => {
    if (p.estoque === null || p.estoque === undefined) return null;
    if (p.estoque <= 0) return <Badge className="bg-red-100 text-red-700 hover:bg-red-100 text-xs"><XCircleIcon className="h-3 w-3 mr-1" />{language === 'pt' ? 'Esgotado' : 'Out of stock'}</Badge>;
    if (p.estoque <= 5) return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 text-xs"><AlertTriangleIcon className="h-3 w-3 mr-1" />{language === 'pt' ? `Baixo: ${p.estoque}` : `Low: ${p.estoque}`}</Badge>;
    return null;
  };

  if (!empresa) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <PackageIcon className="h-16 w-16 text-muted-foreground mb-4" />
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
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('catalogo.title')}</h1>
            <p className="text-muted-foreground">{filtered.length} {t('catalogo.total')}</p>
          </div>
          <Badge className="bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10 self-start">{empresa.nome_empresa}</Badge>
        </div>

        {/* Stock Summary Alert */}
        {stockSummary && (stockSummary.fora_estoque > 0 || stockSummary.estoque_baixo > 0) && (
          <Card className="mb-6 border-amber-200 bg-amber-50/50">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <AlertTriangleIcon className="h-5 w-5 text-amber-600" />
                  <span className="font-semibold text-amber-900">{language === 'pt' ? 'Alertas de Estoque' : 'Stock Alerts'}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {stockSummary.fora_estoque > 0 && (
                    <Badge className="bg-red-100 text-red-700 hover:bg-red-100 cursor-pointer" onClick={() => setStockFilter('out_of_stock')}>
                      <PackageXIcon className="h-3 w-3 mr-1" />
                      {stockSummary.fora_estoque} {language === 'pt' ? 'esgotado(s)' : 'out of stock'}
                    </Badge>
                  )}
                  {stockSummary.estoque_baixo > 0 && (
                    <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 cursor-pointer" onClick={() => setStockFilter('low_stock')}>
                      <TrendingDownIcon className="h-3 w-3 mr-1" />
                      {stockSummary.estoque_baixo} {language === 'pt' ? 'estoque baixo' : 'low stock'}
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2 ml-auto">
                  <Button size="sm" variant="outline" onClick={handleProcessOrderStock} disabled={processingStock} className="border-amber-400 text-amber-700 hover:bg-amber-100">
                    {processingStock ? <Loader2Icon className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCwIcon className="h-3 w-3 mr-1" />}
                    {language === 'pt' ? 'Baixa Pedidos' : 'Process Orders'}
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleBulkFetchPrices} disabled={bulkFetching} className="border-[#A3966A] text-[#A3966A] hover:bg-[#A3966A]/10">
                    {bulkFetching ? <Loader2Icon className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCwIcon className="h-3 w-3 mr-1" />}
                    {language === 'pt' ? 'Atualizar Preços' : 'Update Prices'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Search & Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('common.search')} className="pl-10" />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            <FilterIcon className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-2" />
            {categories.map((cat) => (
              <Button key={cat} variant={filterCat === cat ? 'default' : 'outline'} size="sm" onClick={() => setFilterCat(cat)}
                className={`capitalize flex-shrink-0 ${filterCat === cat ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white' : ''}`}>
                {cat === 'all' ? t('shop.all') : cat}
              </Button>
            ))}
          </div>
        </div>

        {/* Stock filter */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
          {([
            { key: 'all' as StockFilter, label: language === 'pt' ? 'Todos' : 'All', icon: null },
            { key: 'in_stock' as StockFilter, label: language === 'pt' ? 'Em Estoque' : 'In Stock', icon: '✅' },
            { key: 'low_stock' as StockFilter, label: language === 'pt' ? 'Estoque Baixo' : 'Low Stock', icon: '⚠️' },
            { key: 'out_of_stock' as StockFilter, label: language === 'pt' ? 'Esgotado' : 'Out of Stock', icon: '❌' },
          ]).map((sf) => (
            <Button
              key={sf.key}
              variant={stockFilter === sf.key ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStockFilter(sf.key)}
              className={`flex-shrink-0 ${stockFilter === sf.key ? 'bg-[#895D2B] hover:bg-[#A3966A] text-white' : ''}`}
            >
              {sf.icon && <span className="mr-1">{sf.icon}</span>}
              {sf.label}
              {sf.key === 'out_of_stock' && stockSummary?.fora_estoque ? ` (${stockSummary.fora_estoque})` : ''}
              {sf.key === 'low_stock' && stockSummary?.estoque_baixo ? ` (${stockSummary.estoque_baixo})` : ''}
            </Button>
          ))}
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} className="animate-pulse"><div className="aspect-square bg-muted" /><CardContent className="p-4"><div className="h-4 bg-muted rounded mb-2 w-3/4" /></CardContent></Card>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Card className="text-center py-16">
            <CardContent>
              <PackageIcon className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <h3 className="text-lg font-semibold mb-2">{t('catalogo.noProducts')}</h3>
              <p className="text-muted-foreground mb-4">{t('catalogo.importFirst')}</p>
              <Button onClick={() => navigate('/import')} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">{t('nav.import')}</Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filtered.map((p) => {
              const isOutOfStock = p.estoque !== null && p.estoque !== undefined && p.estoque <= 0;
              return (
                <Card key={p.id} className={`overflow-hidden group hover:shadow-lg transition-all duration-300 hover:-translate-y-1 ${isOutOfStock ? 'opacity-70 border-red-200' : ''}`}>
                  <div className="aspect-square overflow-hidden bg-muted relative">
                    {p.imagem_url ? (
                      <img src={p.imagem_url} alt={p.nome} className={`w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 ${isOutOfStock ? 'grayscale' : ''}`} />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center"><PackageIcon className="h-12 w-12 text-muted-foreground" /></div>
                    )}
                    <div className="absolute top-3 left-3 flex flex-col gap-1">
                      {p.categoria && <Badge className="bg-white/90 text-foreground hover:bg-white/90 capitalize">{p.categoria}</Badge>}
                      {isOutOfStock ? (
                        <Badge className="bg-red-500 text-white hover:bg-red-500">{language === 'pt' ? '❌ Esgotado' : '❌ Out of stock'}</Badge>
                      ) : (
                        <Badge className={p.ativo !== false ? 'bg-green-100 text-green-700 hover:bg-green-100' : 'bg-red-100 text-red-700 hover:bg-red-100'}>
                          {p.ativo !== false ? t('catalogo.active') : t('catalogo.inactive')}
                        </Badge>
                      )}
                      {getStockBadge(p)}
                    </div>
                    {/* Price fetch button */}
                    {p.link_produto && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleFetchPrice(p); }}
                        disabled={fetchingPrice === p.id}
                        className="absolute top-3 right-3 bg-white/90 hover:bg-white rounded-full p-1.5 shadow-sm transition-all"
                        title={language === 'pt' ? 'Atualizar preço via site' : 'Update price from website'}
                      >
                        {fetchingPrice === p.id ? (
                          <Loader2Icon className="h-4 w-4 text-[#A3966A] animate-spin" />
                        ) : (
                          <RefreshCwIcon className="h-4 w-4 text-[#A3966A]" />
                        )}
                      </button>
                    )}
                  </div>
                  <CardContent className="p-4">
                    <h3 className="font-semibold text-foreground mb-1 line-clamp-1">{p.nome}</h3>
                    <p className="text-xs text-muted-foreground mb-2">{t('catalogo.sku')}: {p.sku}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-foreground">{p.preco ? `R$ ${p.preco.toFixed(2)}` : '-'}</span>
                      <span className={`text-xs font-medium ${isOutOfStock ? 'text-red-600' : p.estoque !== null && p.estoque !== undefined && p.estoque <= 5 ? 'text-amber-600' : 'text-muted-foreground'}`}>
                        {t('catalogo.stock')}: {p.estoque ?? '-'}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {p.cor && <Badge variant="outline" className="text-xs">{p.cor}</Badge>}
                      {p.tamanho && <Badge variant="outline" className="text-xs">{p.tamanho}</Badge>}
                      {p.colecao && <Badge variant="outline" className="text-xs">{p.colecao}</Badge>}
                    </div>
                    {p.link_produto && (
                      <a href={p.link_produto} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-[#A3966A] hover:underline mt-2">
                        <ExternalLinkIcon className="h-3 w-3" />
                        {language === 'pt' ? 'Ver no site' : 'View on site'}
                      </a>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}