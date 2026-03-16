import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  BrainIcon, Loader2Icon, AlertCircleIcon, BarChart3Icon,
  MousePointerClickIcon, ThumbsUpIcon, ThumbsDownIcon, SparklesIcon,
  RefreshCwIcon, TrendingUpIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

interface Analytics {
  total_recommendations: number;
  total_clicked: number;
  total_approved: number;
  click_rate: number;
  approval_rate: number;
  by_occasion: Record<string, number>;
  recent_logs: Array<{
    id: number;
    cliente_id: number | null;
    produtos_recomendados: string;
    ocasiao: string | null;
    fonte: string;
    clicado: boolean;
    aprovado_marca: boolean | null;
    feedback: string | null;
    created_at: string | null;
  }>;
}

export default function AILearningPage() {
  const { language } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();

  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<number | null>(null);

  useEffect(() => { if (empresa) loadAnalytics(); }, [empresa]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/engine/analytics',
        method: 'GET',
        data: { empresa_id: empresa!.id },
      });
      setAnalytics(res.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleApprove = async (logId: number, aprovado: boolean) => {
    setApprovingId(logId);
    try {
      await client.apiCall.invoke({
        url: '/api/v1/engine/approve-recommendation',
        method: 'POST',
        data: { log_id: logId, aprovado, feedback: aprovado ? 'Aprovado pela marca' : 'Rejeitado pela marca' },
      });
      toast.success(aprovado ? (language === 'pt' ? 'Aprovado!' : 'Approved!') : (language === 'pt' ? 'Rejeitado' : 'Rejected'));
      loadAnalytics();
    } catch (err) { console.error(err); toast.error('Failed'); }
    finally { setApprovingId(null); }
  };

  if (!empresa) {
    return (
      <div className="min-h-screen bg-background"><Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <AlertCircleIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <Button onClick={() => navigate('/empresa')} className="bg-[#A3966A] hover:bg-[#895D2B] text-white mt-4">{language === 'pt' ? 'Ir para Empresa' : 'Go to Company'}</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">
              {language === 'pt' ? 'Painel de Aprendizado da IA' : 'AI Learning Dashboard'}
            </h1>
            <p className="text-muted-foreground">
              {language === 'pt' ? 'Acompanhe e ajuste a inteligência de recomendação' : 'Track and adjust recommendation intelligence'}
            </p>
            <Badge className="mt-2 bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10">{empresa.nome_empresa}</Badge>
          </div>
          <Button variant="outline" onClick={loadAnalytics} disabled={loading}>
            <RefreshCwIcon className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            {language === 'pt' ? 'Atualizar' : 'Refresh'}
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12"><Loader2Icon className="h-8 w-8 animate-spin text-[#A3966A]" /></div>
        ) : !analytics ? (
          <Card>
            <CardContent className="p-12 text-center">
              <BrainIcon className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-bold mb-2">{language === 'pt' ? 'Sem dados ainda' : 'No data yet'}</h3>
              <p className="text-muted-foreground">{language === 'pt' ? 'Gere recomendações para ver análises aqui' : 'Generate recommendations to see analytics here'}</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {[
                { icon: SparklesIcon, label: language === 'pt' ? 'Total Recomendações' : 'Total Recommendations', value: analytics.total_recommendations, color: '#A3966A' },
                { icon: MousePointerClickIcon, label: language === 'pt' ? 'Cliques' : 'Clicks', value: `${analytics.total_clicked} (${analytics.click_rate}%)`, color: '#2563EB' },
                { icon: ThumbsUpIcon, label: language === 'pt' ? 'Aprovadas' : 'Approved', value: `${analytics.total_approved} (${analytics.approval_rate}%)`, color: '#16A34A' },
                { icon: TrendingUpIcon, label: language === 'pt' ? 'Taxa de Aprovação' : 'Approval Rate', value: `${analytics.approval_rate}%`, color: '#D97706' },
              ].map((stat) => (
                <Card key={stat.label}>
                  <CardContent className="p-5">
                    <stat.icon className="h-6 w-6 mb-2" style={{ color: stat.color }} />
                    <p className="text-2xl font-bold text-foreground">{stat.value}</p>
                    <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* By Occasion */}
            {Object.keys(analytics.by_occasion).length > 0 && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><BarChart3Icon className="h-5 w-5 text-[#A3966A]" />{language === 'pt' ? 'Por Ocasião' : 'By Occasion'}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-3">
                    {Object.entries(analytics.by_occasion).map(([occasion, count]) => (
                      <div key={occasion} className="flex items-center gap-2 bg-muted/50 rounded-lg px-4 py-2">
                        <span className="font-medium text-foreground capitalize">{occasion}</span>
                        <Badge variant="secondary">{count}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Recent Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <SparklesIcon className="h-5 w-5 text-[#A3966A]" />
                  {language === 'pt' ? 'Recomendações Recentes' : 'Recent Recommendations'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {analytics.recent_logs.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">{language === 'pt' ? 'Nenhuma recomendação gerada ainda' : 'No recommendations generated yet'}</p>
                ) : (
                  <div className="space-y-3">
                    {analytics.recent_logs.map((log) => {
                      let productIds: number[] = [];
                      try { productIds = JSON.parse(log.produtos_recomendados || '[]'); } catch { /* empty */ }
                      return (
                        <div key={log.id} className="flex items-center gap-4 p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="secondary" className="text-xs">{log.fonte}</Badge>
                              {log.ocasiao && <Badge variant="outline" className="text-xs capitalize">{log.ocasiao}</Badge>}
                              {log.clicado && <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100 text-xs">{language === 'pt' ? 'Clicado' : 'Clicked'}</Badge>}
                              {log.aprovado_marca === true && <Badge className="bg-green-100 text-green-700 hover:bg-green-100 text-xs">✓</Badge>}
                              {log.aprovado_marca === false && <Badge className="bg-red-100 text-red-700 hover:bg-red-100 text-xs">✗</Badge>}
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {productIds.length} {language === 'pt' ? 'produtos recomendados' : 'products recommended'}
                              {log.cliente_id ? ` · ${language === 'pt' ? 'Cliente' : 'Customer'} #${log.cliente_id}` : ''}
                            </p>
                            {log.feedback && <p className="text-xs text-muted-foreground italic mt-1">{log.feedback}</p>}
                          </div>
                          <div className="flex gap-1 flex-shrink-0">
                            <Button size="sm" variant="ghost" disabled={approvingId === log.id || log.aprovado_marca === true} onClick={() => handleApprove(log.id, true)} className="text-green-600 hover:text-green-700">
                              <ThumbsUpIcon className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" disabled={approvingId === log.id || log.aprovado_marca === false} onClick={() => handleApprove(log.id, false)} className="text-red-500 hover:text-red-700">
                              <ThumbsDownIcon className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}