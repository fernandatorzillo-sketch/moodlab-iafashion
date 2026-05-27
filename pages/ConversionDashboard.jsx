import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";

const API_BASE = "https://closet-moodlab.onrender.com";
const GOLD = "#b7a56a";
const GOLD_DARK = "#9a8a52";
const GOLD_LIGHT = "#f5ece0";
const COLORS = ["#b7a56a","#5a8a6a","#6a7a9a","#a86a5a","#7a6a9a","#6a9a8a"];

const SOURCE_LABELS = {
  widget_stylist_chat: "Personal Shopper",
  widget_pdp: "Widget Produto",
  widget_category: "Widget Categoria",
};

function fmt(n) { return Number(n || 0).toLocaleString("pt-BR"); }
function fmtBRL(n) {
  return Number(n || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function KPI({ label, value, sub, icon, accent = GOLD, big = false }) {
  return (
    <div style={{
      background:"#fff", border:`1.5px solid ${accent}22`,
      borderRadius:14, padding:"18px 20px", flex:1, minWidth:130,
    }}>
      <div style={{ fontSize:20, marginBottom:4 }}>{icon}</div>
      <div style={{ fontSize:11, color:"#9a8f83", fontWeight:700,
        textTransform:"uppercase", letterSpacing:0.8, marginBottom:4 }}>{label}</div>
      <div style={{ fontSize: big ? 32 : 26, fontWeight:800, color:accent, lineHeight:1 }}>{value}</div>
      {sub && <div style={{ fontSize:11, color:"#b0a090", marginTop:4 }}>{sub}</div>}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ background:"#fff", border:"1px solid #e8dece",
      borderRadius:16, padding:24, marginBottom:22 }}>
      <h2 style={{ margin:"0 0 16px", fontSize:16, color:"#2f2a24",
        fontFamily:"Georgia,serif", display:"flex", alignItems:"center", gap:8 }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

export default function ConversionDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/customer-closet/conversion-stats`);
      const d = await res.json();
      setData(d);
    } catch { setError("Erro ao carregar métricas."); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  if (loading) return (
    <div style={{ padding:60, textAlign:"center", color:"#9a8f83",
      fontFamily:"Georgia,serif", fontSize:16 }}>✦ Carregando…</div>
  );
  if (error) return <div style={{ padding:40, color:"#a04f4f" }}>{error}</div>;

  const byDay = (data?.by_day || []).slice(0,30).reverse();
  const byHour = data?.by_hour || [];
  const bySource = (data?.by_source || []).map(s => ({
    ...s, label: SOURCE_LABELS[s.source] || s.source,
  }));
  const topProducts = (data?.top_products || []).slice(0,8);
  const topRequests = (data?.top_requests || []).slice(0,8);
  const ranking = data?.ranking || [];

  return (
    <div style={{ fontFamily:"Arial,sans-serif", padding:"28px 24px",
      background:"#faf7f2", minHeight:"100vh" }}>

      {/* Header */}
      <div style={{ display:"flex", justifyContent:"space-between",
        alignItems:"flex-start", marginBottom:24 }}>
        <div>
          <h1 style={{ margin:0, fontSize:24, fontFamily:"Georgia,serif", color:"#2f2a24" }}>
            ✦ Dashboard · Personal Shopper
          </h1>
          <p style={{ margin:"4px 0 0", color:"#9a8f83", fontSize:13 }}>
            Performance do widget MoodLab · Água de Coco
          </p>
        </div>
        <button onClick={load} style={{ background:GOLD, color:"#fff", border:"none",
          borderRadius:999, padding:"9px 20px", fontSize:13, fontWeight:700,
          cursor:"pointer" }}>↻ Atualizar</button>
      </div>

      {/* KPIs Principais */}
      <div style={{ display:"flex", flexWrap:"wrap", gap:12, marginBottom:22 }}>
        <KPI label="Conversas hoje" value={fmt(data?.last_24h)} icon="💬"
          sub="últimas 24h" accent={GOLD} big />
        <KPI label="Últimos 7 dias" value={fmt(data?.last_7d)} icon="📈"
          sub="interações" accent="#5a8a6a" />
        <KPI label="Clientes únicos" value={fmt(data?.unique_users)} icon="👤"
          sub="total" accent="#6a7a9a" />
        <KPI label="Sessões chat" value={fmt(data?.chat_sessions)} icon="🤖"
          sub="personal shopper" accent={GOLD_DARK} />
      </div>

      {/* KPIs Conversão */}
      <div style={{ background:`linear-gradient(135deg, ${GOLD}18, ${GOLD}08)`,
        border:`1px solid ${GOLD}44`, borderRadius:16, padding:"20px 24px",
        marginBottom:22 }}>
        <div style={{ fontSize:13, fontWeight:700, color:GOLD_DARK,
          textTransform:"uppercase", letterSpacing:1, marginBottom:14 }}>
          💰 Funil de Conversão — Widget → Compra (janela 72h)
        </div>
        <div style={{ display:"flex", flexWrap:"wrap", gap:16 }}>
          <KPI label="Usuários do widget" value={fmt(data?.widget_users)}
            icon="🛍️" accent={GOLD} />
          <KPI label="Compraram depois" value={fmt(data?.converted_users)}
            icon="✅" accent="#5a8a6a" />
          <KPI label="Taxa de conversão" value={`${data?.conversion_rate || 0}%`}
            icon="📊" accent="#5a8a6a" big />
          <KPI label="Pedidos gerados" value={fmt(data?.orders_after_chat)}
            icon="📦" accent="#6a7a9a" />
          <KPI label="Receita atribuída" value={fmtBRL(data?.revenue_after_chat)}
            icon="💵" accent={GOLD_DARK} big />
        </div>
        <p style={{ margin:"12px 0 0", fontSize:11, color:"#9a8f83" }}>
          * Clientes que usaram o Personal Shopper e fizeram pedido nas 72h seguintes
        </p>
      </div>

      {/* Linha temporal */}
      {byDay.length > 0 && (
        <Section title="📅 Interações diárias — últimos 30 dias">
          <ResponsiveContainer width="100%" height={190}>
            <LineChart data={byDay}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0e8dc" />
              <XAxis dataKey="day" tick={{ fontSize:11 }}
                tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fontSize:11 }} />
              <Tooltip contentStyle={{ borderRadius:10, border:"1px solid #e8dece", fontSize:12 }}
                formatter={(v,n) => [fmt(v), n==="clicks"?"Interações":"Clientes"]} />
              <Line type="monotone" dataKey="clicks" stroke={GOLD}
                strokeWidth={2.5} dot={{ fill:GOLD, r:3 }} name="clicks" />
              <Line type="monotone" dataKey="users" stroke="#5a8a6a"
                strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="users" />
              <Legend formatter={v => v==="clicks"?"Interações":"Clientes únicos"} />
            </LineChart>
          </ResponsiveContainer>
        </Section>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20, marginBottom:22 }}>
        {/* Horários de pico */}
        {byHour.length > 0 && (
          <Section title="🕐 Horários de pico (horário de Brasília)">
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={byHour}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0e8dc" />
                <XAxis dataKey="hour" tick={{ fontSize:11 }}
                  tickFormatter={h => `${h}h`} />
                <YAxis tick={{ fontSize:11 }} />
                <Tooltip contentStyle={{ borderRadius:10, border:"1px solid #e8dece" }}
                  formatter={v => [fmt(v),"Interações"]}
                  labelFormatter={h => `${h}h`} />
                <Bar dataKey="clicks" fill={GOLD} radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </Section>
        )}

        {/* Por canal */}
        {bySource.length > 0 && (
          <Section title="📡 Por canal">
            <ResponsiveContainer width="100%" height={170}>
              <PieChart>
                <Pie data={bySource} dataKey="clicks" nameKey="label"
                  cx="50%" cy="50%" outerRadius={65}
                  label={({label,percent}) =>
                    percent > 0.05 ? `${(percent*100).toFixed(0)}%` : ""}
                  labelLine={false}>
                  {bySource.map((_,i) =>
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={v => [fmt(v),"Interações"]} />
                <Legend formatter={(_,e) => e.payload.label} />
              </PieChart>
            </ResponsiveContainer>
          </Section>
        )}
      </div>

      {/* Ranking de clientes */}
      {ranking.length > 0 && (
        <Section title="🏅 Ranking de clientes — uso do Personal Shopper">
          <div style={{ overflowX:"auto" }}>
            <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
              <thead>
                <tr style={{ borderBottom:`2px solid ${GOLD_LIGHT}` }}>
                  {["#","Cliente","Dias de uso","Interações","Última conversa",
                    "Pedidos","Total gasto"].map(h => (
                    <th key={h} style={{ textAlign:"left", padding:"8px 10px",
                      color:"#9a8f83", fontWeight:700, whiteSpace:"nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ranking.map((r,i) => (
                  <tr key={i} style={{ borderBottom:"1px solid #f5ede0",
                    background: i < 3 ? `${GOLD}08` : "transparent" }}>
                    <td style={{ padding:"9px 10px", fontWeight:700,
                      color: i===0?"#b7960a":i===1?"#9a9a9a":i===2?"#c47a3a":"#9a8f83" }}>
                      {i===0?"🥇":i===1?"🥈":i===2?"🥉":i+1}
                    </td>
                    <td style={{ padding:"9px 10px", fontWeight:600, color:"#2f2a24" }}>
                      {r.email}
                    </td>
                    <td style={{ padding:"9px 10px", textAlign:"center" }}>
                      {r.dias_de_uso}
                    </td>
                    <td style={{ padding:"9px 10px", textAlign:"center" }}>
                      <span style={{ background:GOLD_LIGHT, color:GOLD_DARK,
                        borderRadius:999, padding:"2px 10px", fontWeight:700 }}>
                        {fmt(r.interacoes)}
                      </span>
                    </td>
                    <td style={{ padding:"9px 10px", color:"#9a8f83" }}>
                      {r.ultima_interacao}
                    </td>
                    <td style={{ padding:"9px 10px", textAlign:"center",
                      fontWeight: r.pedidos > 0 ? 700 : 400,
                      color: r.pedidos > 0 ? "#5a8a6a" : "#9a8f83" }}>
                      {r.pedidos > 0 ? `✅ ${r.pedidos}` : "—"}
                    </td>
                    <td style={{ padding:"9px 10px", fontWeight: r.total_gasto > 0 ? 700 : 400,
                      color: r.total_gasto > 0 ? GOLD_DARK : "#9a8f83" }}>
                      {r.total_gasto > 0 ? fmtBRL(r.total_gasto) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
        {/* O que pedem */}
        {topRequests.length > 0 && (
          <Section title="💬 O que os clientes estão pedindo">
            {topRequests.map((r,i) => (
              <div key={i} style={{ display:"flex", justifyContent:"space-between",
                alignItems:"center", padding:"7px 0",
                borderBottom:"1px solid #f5ede0" }}>
                <span style={{ fontSize:12, color:"#2f2a24", flex:1, paddingRight:10 }}>
                  "{r.request?.slice(0,55)}{r.request?.length>55?"…":""}"
                </span>
                <span style={{ background:GOLD_LIGHT, color:GOLD_DARK,
                  borderRadius:999, padding:"2px 9px", fontSize:11,
                  fontWeight:700, whiteSpace:"nowrap" }}>{r.count}x</span>
              </div>
            ))}
          </Section>
        )}

        {/* Top produtos */}
        {topProducts.length > 0 && (
          <Section title="🏆 Produtos mais clicados">
            {topProducts.map((p,i) => (
              <div key={i} style={{ display:"flex", justifyContent:"space-between",
                alignItems:"center", padding:"7px 0",
                borderBottom:"1px solid #f5ede0" }}>
                <div>
                  <div style={{ fontSize:12, fontWeight:600, color:"#2f2a24" }}>
                    {i+1}. {p.name || p.product_id}
                  </div>
                  {p.category && <div style={{ fontSize:11, color:"#9a8f83" }}>{p.category}</div>}
                </div>
                <span style={{ background:GOLD_LIGHT, color:GOLD_DARK,
                  borderRadius:999, padding:"2px 9px", fontSize:11,
                  fontWeight:700 }}>{fmt(p.clicks)}</span>
              </div>
            ))}
          </Section>
        )}
      </div>
    </div>
  );
}
