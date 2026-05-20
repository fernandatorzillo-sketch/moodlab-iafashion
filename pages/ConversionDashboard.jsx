import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import {
  MousePointerClickIcon,
  ShoppingBagIcon,
  TrendingUpIcon,
  RefreshCwIcon,
  Loader2Icon,
  ZapIcon,
  BarChart3Icon,
  CalendarIcon,
} from 'lucide-react';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

// ─── helpers ────────────────────────────────────────────────────────────────

function pct(num, den) {
  if (!den || den === 0) return '0%';
  return ((num / den) * 100).toFixed(1) + '%';
}

function fmt(n) {
  return (n ?? 0).toLocaleString('pt-BR');
}

// ─── sub-components ─────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, sub, accent }) {
  const colors = {
    gold:  { bg: 'bg-[#A3966A]/10', text: 'text-[#A3966A]', border: 'border-[#A3966A]/20' },
    green: { bg: 'bg-emerald-50',   text: 'text-emerald-600', border: 'border-emerald-100' },
    blue:  { bg: 'bg-sky-50',       text: 'text-sky-600',     border: 'border-sky-100' },
    slate: { bg: 'bg-slate-50',     text: 'text-slate-500',   border: 'border-slate-100' },
  };
  const c = colors[accent] ?? colors.slate;

  return (
    <Card className={`border ${c.border} shadow-sm`}>
      <CardContent className="p-5 flex items-start gap-4">
        <div className={`p-2.5 rounded-xl ${c.bg}`}>
          <Icon className={`w-5 h-5 ${c.text}`} />
        </div>
        <div>
          <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-0.5">{label}</p>
          <p className="text-2xl font-bold text-[#1A1A1A] leading-none">{value}</p>
          {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

function FunnelBar({ label, value, max, color, pctLabel }) {
  const width = max > 0 ? Math.max(4, (value / max) * 100) : 4;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-sm">
        <span className="text-slate-600 font-medium">{label}</span>
        <span className="text-slate-800 font-semibold tabular-nums">
          {fmt(value)} <span className="text-slate-400 font-normal text-xs">({pctLabel})</span>
        </span>
      </div>
      <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

function OccasionRow({ ocasiao, clicks, total }) {
  const rate = total > 0 ? ((clicks / total) * 100).toFixed(0) : 0;
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-50 last:border-0">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[#A3966A]" />
        <span className="text-sm text-slate-700 capitalize">{ocasiao || 'geral'}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-400">{fmt(total)} rec.</span>
        <Badge variant="outline" className="text-xs border-[#A3966A]/30 text-[#895D2B]">
          {rate}% CTR
        </Badge>
      </div>
    </div>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

export default function ConversionDashboard() {
  const { empresa } = useEmpresa();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [clicks, setClicks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30); // days

  useEffect(() => {
    if (empresa) load();
  }, [empresa, period]);

  const load = async () => {
    setLoading(true);
    try {
      // 1. recommendation_logs — geradas + clicadas
      const logsRes = await client.apiCall.invoke({
        url: '/api/v1/entities/recommendation_logs',
        method: 'GET',
        data: {
          limit: 2000,
          sort: '-created_at',
          query: JSON.stringify({ empresa_id: empresa.id }),
        },
      });

      // 2. recommendation_clicks — cliques do widget público
      let clicksData = [];
      try {
        const clicksRes = await client.apiCall.invoke({
          url: '/api/v1/entities/recommendation_clicks',
          method: 'GET',
          data: { limit: 2000, sort: '-clicked_at' },
        });
        clicksData = clicksRes?.data?.items ?? [];
      } catch (_) {
        // tabela pode ainda não ter endpoint dedicado — usa logs
      }

      const logs = logsRes?.data?.items ?? [];

      // filtra pelo período
      const cutoff = new Date();
      cutoff.setDate(cutoff.getDate() - period);
      const recent = logs.filter(l => {
        if (!l.created_at) return true;
        return new Date(l.created_at) >= cutoff;
      });

      // agrupa métricas
      const total = recent.length;
      const clicked = recent.filter(l => l.clicado).length;
      const approved = recent.filter(l => l.aprovado_marca).length;

      // por ocasião
      const byOccasion = {};
      for (const l of recent) {
        const k = l.ocasiao || 'geral';
        if (!byOccasion[k]) byOccasion[k] = { total: 0, clicked: 0 };
        byOccasion[k].total++;
        if (l.clicado) byOccasion[k].clicked++;
      }

      // por fonte
      const bySource = {};
      for (const l of recent) {
        const k = l.fonte || 'desconhecida';
        if (!bySource[k]) bySource[k] = 0;
        bySource[k]++;
      }

      setData({ total, clicked, approved, byOccasion, bySource, logs: recent });
      setClicks(clicksData);
    } catch (err) {
      console.error(err);
      toast.error('Erro ao carregar dados de conversão');
    } finally {
      setLoading(false);
    }
  };

  // ── guard ─────────────────────────────────────────────────────────────────
  if (!empresa) {
    return (
      <div className="min-h-screen bg-white flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <BarChart3Icon className="w-10 h-10 text-slate-300 mx-auto" />
            <p className="text-slate-500 text-sm">Selecione uma empresa para ver os dados.</p>
            <Button variant="outline" size="sm" onClick={() => navigate('/empresa')}>
              Configurar empresa
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const total    = data?.total ?? 0;
  const clicked  = data?.clicked ?? 0;
  const approved = data?.approved ?? 0;
  const ctr      = pct(clicked, total);
  const approvalRate = pct(approved, total);

  return (
    <div className="min-h-screen bg-[#FAFAF9] font-sans">
      <Header />

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-8">

        {/* ── título ───────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#1A1A1A]" style={{ fontFamily: "'DM Serif Display', serif" }}>
              Funil de Conversão
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Recomendações geradas → cliques → aprovações
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* seletor de período */}
            <div className="flex border border-slate-200 rounded-lg overflow-hidden text-xs font-medium">
              {[7, 30, 90].map(d => (
                <button
                  key={d}
                  onClick={() => setPeriod(d)}
                  className={`px-3 py-1.5 transition-colors ${
                    period === d
                      ? 'bg-[#A3966A] text-white'
                      : 'text-slate-500 hover:bg-slate-50'
                  }`}
                >
                  {d}d
                </button>
              ))}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={load}
              disabled={loading}
              className="border-slate-200"
            >
              {loading
                ? <Loader2Icon className="w-4 h-4 animate-spin" />
                : <RefreshCwIcon className="w-4 h-4" />
              }
            </Button>
          </div>
        </div>

        {loading && !data ? (
          <div className="flex items-center justify-center py-24">
            <Loader2Icon className="w-6 h-6 animate-spin text-[#A3966A]" />
          </div>
        ) : (
          <>
            {/* ── KPI cards ─────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard
                icon={ZapIcon}
                label="Recomendações"
                value={fmt(total)}
                sub={`últimos ${period} dias`}
                accent="gold"
              />
              <StatCard
                icon={MousePointerClickIcon}
                label="Cliques"
                value={fmt(clicked)}
                sub={`CTR ${ctr}`}
                accent="blue"
              />
              <StatCard
                icon={TrendingUpIcon}
                label="Taxa de Clique"
                value={ctr}
                sub="rec → clique"
                accent="green"
              />
              <StatCard
                icon={ShoppingBagIcon}
                label="Aprovações"
                value={fmt(approved)}
                sub={`${approvalRate} das rec.`}
                accent="slate"
              />
            </div>

            {/* ── funil visual ──────────────────────────────────────────── */}
            <Card className="border border-slate-100 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold text-[#1A1A1A] flex items-center gap-2">
                  <BarChart3Icon className="w-4 h-4 text-[#A3966A]" />
                  Funil de Engajamento
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-2">
                <FunnelBar
                  label="Recomendações geradas"
                  value={total}
                  max={total}
                  color="bg-[#A3966A]"
                  pctLabel="100%"
                />
                <FunnelBar
                  label="Clicaram em algum produto"
                  value={clicked}
                  max={total}
                  color="bg-sky-400"
                  pctLabel={ctr}
                />
                <FunnelBar
                  label="Aprovadas pela marca"
                  value={approved}
                  max={total}
                  color="bg-emerald-400"
                  pctLabel={approvalRate}
                />
                {clicks.length > 0 && (
                  <FunnelBar
                    label="Cliques diretos no widget"
                    value={clicks.length}
                    max={total}
                    color="bg-violet-400"
                    pctLabel={pct(clicks.length, total)}
                  />
                )}
              </CardContent>
            </Card>

            {/* ── por ocasião ──────────────────────────────────────────── */}
            {data?.byOccasion && Object.keys(data.byOccasion).length > 0 && (
              <Card className="border border-slate-100 shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-semibold text-[#1A1A1A] flex items-center gap-2">
                    <CalendarIcon className="w-4 h-4 text-[#A3966A]" />
                    CTR por Ocasião
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  {Object.entries(data.byOccasion)
                    .sort((a, b) => b[1].total - a[1].total)
                    .map(([occ, { total: t, clicked: c }]) => (
                      <OccasionRow key={occ} ocasiao={occ} clicks={c} total={t} />
                    ))
                  }
                </CardContent>
              </Card>
            )}

            {/* ── estado vazio ─────────────────────────────────────────── */}
            {total === 0 && (
              <div className="text-center py-16 text-slate-400 space-y-2">
                <BarChart3Icon className="w-10 h-10 mx-auto opacity-30" />
                <p className="text-sm">Nenhuma recomendação registrada nos últimos {period} dias.</p>
                <p className="text-xs">As métricas aparecerão assim que o engine começar a gerar recomendações.</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
