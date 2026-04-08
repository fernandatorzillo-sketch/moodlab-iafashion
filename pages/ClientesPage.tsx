import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { UsersIcon, SearchIcon, ShirtIcon, ShoppingBagIcon } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

interface Cliente {
  id: number;
  nome: string;
  email: string;
  telefone: string;
  genero: string;
  cidade: string;
  estado: string;
  estilo_resumo: string;
  tamanho_top: string;
  tamanho_bottom: string;
  tamanho_dress: string;
}

export default function ClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const { t } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();

  useEffect(() => {
    if (empresa) fetchClientes();
    else setLoading(false);
  }, [empresa]);

  const fetchClientes = async () => {
    try {
      const res = await client.entities.clientes.query({
        query: { empresa_id: empresa!.id },
        limit: 200,
        sort: '-id',
      });
      setClientes(res.data?.items || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const filtered = clientes.filter((c) =>
    !search || c.nome?.toLowerCase().includes(search.toLowerCase()) || c.email?.toLowerCase().includes(search.toLowerCase())
  );

  if (!empresa) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <UsersIcon className="h-16 w-16 text-muted-foreground mb-4" />
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
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('clientes.title')}</h1>
            <p className="text-muted-foreground">{filtered.length} {t('clientes.total')}</p>
          </div>
          <Badge className="bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10 self-start">{empresa.nome_empresa}</Badge>
        </div>

        {/* Search */}
        <div className="relative mb-6 max-w-md">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('common.search')} className="pl-10" />
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="animate-pulse"><CardContent className="p-5"><div className="h-5 bg-muted rounded mb-3 w-3/4" /><div className="h-4 bg-muted rounded w-1/2" /></CardContent></Card>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Card className="text-center py-16">
            <CardContent>
              <UsersIcon className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <h3 className="text-lg font-semibold mb-2">{t('clientes.noClients')}</h3>
              <p className="text-muted-foreground mb-4">{t('clientes.importFirst')}</p>
              <Button onClick={() => navigate('/import')} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">{t('nav.import')}</Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((c) => (
              <Card key={c.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-foreground text-lg">{c.nome}</h3>
                      <p className="text-sm text-muted-foreground">{c.email}</p>
                      {c.telefone && <p className="text-sm text-muted-foreground">{c.telefone}</p>}
                    </div>
                    {c.genero && <Badge variant="outline" className="capitalize">{c.genero}</Badge>}
                  </div>

                  {(c.cidade || c.estado) && (
                    <p className="text-sm text-muted-foreground mb-2">
                      📍 {[c.cidade, c.estado].filter(Boolean).join(', ')}
                    </p>
                  )}

                  {c.estilo_resumo && (
                    <div className="mb-2">
                      <span className="text-xs font-medium text-[#A3966A]">{t('clientes.style')}:</span>
                      <p className="text-sm text-muted-foreground">{c.estilo_resumo}</p>
                    </div>
                  )}

                  {(c.tamanho_top || c.tamanho_bottom || c.tamanho_dress) && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      <span className="text-xs font-medium text-muted-foreground">{t('clientes.sizes')}:</span>
                      {c.tamanho_top && <Badge variant="secondary" className="text-xs">Top: {c.tamanho_top}</Badge>}
                      {c.tamanho_bottom && <Badge variant="secondary" className="text-xs">Bottom: {c.tamanho_bottom}</Badge>}
                      {c.tamanho_dress && <Badge variant="secondary" className="text-xs">Dress: {c.tamanho_dress}</Badge>}
                    </div>
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