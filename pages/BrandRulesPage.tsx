import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  PlusIcon, Loader2Icon, TrashIcon, ShieldIcon,
  AlertCircleIcon, SlidersHorizontalIcon, XIcon, ToggleLeftIcon, ToggleRightIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

interface BrandRule {
  id?: number;
  rule_type: string;
  rule_value: string;
  descricao: string;
  ativo: boolean;
  prioridade: number;
}

const RULE_TYPES = [
  { value: 'priorizar_estoque', label_pt: 'Priorizar peças com maior estoque', label_en: 'Prioritize items with higher stock' },
  { value: 'priorizar_margem', label_pt: 'Priorizar peças com maior margem', label_en: 'Prioritize higher margin items' },
  { value: 'priorizar_lancamentos', label_pt: 'Priorizar lançamentos', label_en: 'Prioritize new arrivals' },
  { value: 'priorizar_categoria', label_pt: 'Priorizar categoria específica', label_en: 'Prioritize specific category' },
  { value: 'priorizar_colecao', label_pt: 'Priorizar coleção específica', label_en: 'Prioritize specific collection' },
  { value: 'evitar_combinacao', label_pt: 'Evitar combinação específica', label_en: 'Avoid specific combination' },
  { value: 'looks_completos', label_pt: 'Priorizar looks completos', label_en: 'Prioritize complete outfits' },
  { value: 'evitar_contexto', label_pt: 'Evitar produto fora de contexto', label_en: 'Avoid out-of-context products' },
];

export default function BrandRulesPage() {
  const { language } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();

  const [rules, setRules] = useState<BrandRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [newRule, setNewRule] = useState<BrandRule>({ rule_type: 'priorizar_estoque', rule_value: '', descricao: '', ativo: true, prioridade: 5 });
  const [saving, setSaving] = useState(false);

  useEffect(() => { if (empresa) loadRules(); }, [empresa]);

  const loadRules = async () => {
    try {
      const res = await client.entities.brand_rules.query({ query: { empresa_id: empresa!.id }, sort: '-prioridade', limit: 50 });
      setRules(res.data?.items || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSave = async () => {
    if (!empresa) return;
    setSaving(true);
    try {
      await client.entities.brand_rules.create({ data: { ...newRule, empresa_id: empresa.id } });
      toast.success(language === 'pt' ? 'Regra criada!' : 'Rule created!');
      setShowForm(false);
      setNewRule({ rule_type: 'priorizar_estoque', rule_value: '', descricao: '', ativo: true, prioridade: 5 });
      loadRules();
    } catch (err) { console.error(err); toast.error('Failed to save'); }
    finally { setSaving(false); }
  };

  const toggleRule = async (rule: BrandRule) => {
    try {
      await client.entities.brand_rules.update({ id: String(rule.id), data: { ativo: !rule.ativo } });
      loadRules();
    } catch (err) { console.error(err); }
  };

  const deleteRule = async (id: number) => {
    try {
      await client.entities.brand_rules.delete({ id: String(id) });
      toast.success(language === 'pt' ? 'Regra removida!' : 'Rule deleted!');
      loadRules();
    } catch (err) { console.error(err); }
  };

  const getRuleLabel = (type: string) => {
    const rt = RULE_TYPES.find((r) => r.value === type);
    return rt ? (language === 'pt' ? rt.label_pt : rt.label_en) : type;
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
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">
              {language === 'pt' ? 'Regras de Recomendação' : 'Recommendation Rules'}
            </h1>
            <p className="text-muted-foreground">
              {language === 'pt' ? 'Configure as regras comerciais que orientam a IA' : 'Configure business rules that guide the AI'}
            </p>
            <Badge className="mt-2 bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10">{empresa.nome_empresa}</Badge>
          </div>
          <Button onClick={() => setShowForm(true)} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
            <PlusIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Nova Regra' : 'New Rule'}
          </Button>
        </div>

        {/* New Rule Form */}
        {showForm && (
          <Card className="mb-6 border-[#A3966A]/30">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2"><ShieldIcon className="h-5 w-5 text-[#A3966A]" />{language === 'pt' ? 'Nova Regra' : 'New Rule'}</CardTitle>
                <Button variant="ghost" size="icon" onClick={() => setShowForm(false)}><XIcon className="h-4 w-4" /></Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{language === 'pt' ? 'Tipo de Regra' : 'Rule Type'}</Label>
                <select value={newRule.rule_type} onChange={(e) => setNewRule({ ...newRule, rule_type: e.target.value })} className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background mt-1">
                  {RULE_TYPES.map((rt) => <option key={rt.value} value={rt.value}>{language === 'pt' ? rt.label_pt : rt.label_en}</option>)}
                </select>
              </div>
              <div>
                <Label>{language === 'pt' ? 'Valor / Configuração' : 'Value / Configuration'}</Label>
                <Input value={newRule.rule_value} onChange={(e) => setNewRule({ ...newRule, rule_value: e.target.value })} placeholder={language === 'pt' ? 'Ex: vestidos, coleção verão 2026...' : 'Ex: dresses, summer 2026 collection...'} className="mt-1" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'Descrição' : 'Description'}</Label>
                <Input value={newRule.descricao} onChange={(e) => setNewRule({ ...newRule, descricao: e.target.value })} placeholder={language === 'pt' ? 'Descreva a regra...' : 'Describe the rule...'} className="mt-1" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'Prioridade (1-10)' : 'Priority (1-10)'}</Label>
                <Input type="number" min={1} max={10} value={newRule.prioridade} onChange={(e) => setNewRule({ ...newRule, prioridade: parseInt(e.target.value) || 5 })} className="mt-1 w-24" />
              </div>
              <Button onClick={handleSave} disabled={saving} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                {saving ? <Loader2Icon className="h-4 w-4 mr-2 animate-spin" /> : <ShieldIcon className="h-4 w-4 mr-2" />}
                {language === 'pt' ? 'Criar Regra' : 'Create Rule'}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Rules List */}
        {loading ? (
          <div className="flex justify-center py-12"><Loader2Icon className="h-8 w-8 animate-spin text-[#A3966A]" /></div>
        ) : rules.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <SlidersHorizontalIcon className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-bold mb-2">{language === 'pt' ? 'Nenhuma regra configurada' : 'No rules configured'}</h3>
              <p className="text-muted-foreground mb-4">{language === 'pt' ? 'Defina regras para orientar as recomendações da IA' : 'Define rules to guide AI recommendations'}</p>
              <Button onClick={() => setShowForm(true)} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                <PlusIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Criar Primeira Regra' : 'Create First Rule'}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {rules.map((rule) => (
              <Card key={rule.id} className={`transition-all ${!rule.ativo ? 'opacity-50' : ''}`}>
                <CardContent className="p-4 flex items-center gap-4">
                  <button onClick={() => toggleRule(rule)} className="flex-shrink-0">
                    {rule.ativo ? <ToggleRightIcon className="h-6 w-6 text-green-500" /> : <ToggleLeftIcon className="h-6 w-6 text-muted-foreground" />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-foreground">{getRuleLabel(rule.rule_type)}</span>
                      <Badge variant="secondary" className="text-xs">P{rule.prioridade}</Badge>
                    </div>
                    {rule.rule_value && <p className="text-sm text-[#A3966A] font-medium">{rule.rule_value}</p>}
                    {rule.descricao && <p className="text-sm text-muted-foreground">{rule.descricao}</p>}
                  </div>
                  <Button size="sm" variant="ghost" className="text-red-500 hover:text-red-700 flex-shrink-0" onClick={() => rule.id && deleteRule(rule.id)}>
                    <TrashIcon className="h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}