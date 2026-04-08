import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { BuildingIcon, PlusIcon, CheckCircleIcon } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';

interface Empresa {
  id: number;
  nome_empresa: string;
  email_admin: string;
  plataforma_ecommerce?: string;
  erp?: string;
  crm?: string;
}

export default function EmpresaSetupPage() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ nome_empresa: '', email_admin: '', plataforma_ecommerce: '', erp: '', crm: '' });
  const { t } = useLanguage();
  const { empresa: selectedEmpresa, setEmpresa } = useEmpresa();

  useEffect(() => { checkAuth(); }, []);

  const checkAuth = async () => {
    try {
      const res = await client.auth.me();
      if (res?.data) { setUser(res.data); await fetchEmpresas(); }
      else setLoading(false);
    } catch { setUser(null); setLoading(false); }
  };

  const fetchEmpresas = async () => {
    try {
      const res = await client.entities.empresas.query({ query: {}, limit: 50 });
      setEmpresas(res.data?.items || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSave = async () => {
    if (!form.nome_empresa || !form.email_admin) { toast.error('Name and email are required'); return; }
    setSaving(true);
    try {
      const res = await client.entities.empresas.create({
        data: { ...form, created_at: new Date().toISOString().replace('T', ' ').substring(0, 19) },
      });
      const newEmpresa = res.data;
      setEmpresas((prev) => [...prev, newEmpresa]);
      setEmpresa(newEmpresa);
      setShowForm(false);
      setForm({ nome_empresa: '', email_admin: '', plataforma_ecommerce: '', erp: '', crm: '' });
      toast.success(t('empresa.saved'));
    } catch (err) { console.error(err); toast.error('Failed to save'); }
    finally { setSaving(false); }
  };

  const selectEmpresa = (emp: Empresa) => {
    setEmpresa(emp);
    toast.success(`${emp.nome_empresa} ${t('empresa.select').toLowerCase()}`);
  };

  if (!user && !loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <BuildingIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('empresa.signinTitle')}</h2>
          <p className="text-muted-foreground mb-6">{t('empresa.signinDesc')}</p>
          <Button onClick={() => client.auth.toLogin()} className="bg-[#A3966A] hover:bg-[#895D2B] text-white font-semibold">{t('auth.signin')}</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('empresa.title')}</h1>
            <p className="text-muted-foreground">{t('empresa.subtitle')}</p>
          </div>
          <Button onClick={() => setShowForm(true)} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
            <PlusIcon className="h-4 w-4 mr-2" />
            {t('empresa.name')}
          </Button>
        </div>

        {/* Company List */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {empresas.map((emp) => (
            <Card
              key={emp.id}
              className={`cursor-pointer transition-all hover:shadow-md ${selectedEmpresa?.id === emp.id ? 'border-[#A3966A] border-2 shadow-md' : 'border-border'}`}
              onClick={() => selectEmpresa(emp)}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-lg text-foreground">{emp.nome_empresa}</h3>
                    <p className="text-sm text-muted-foreground">{emp.email_admin}</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {emp.plataforma_ecommerce && <span className="text-xs bg-[#A3966A]/10 text-[#A3966A] px-2 py-0.5 rounded">{emp.plataforma_ecommerce}</span>}
                      {emp.erp && <span className="text-xs bg-[#895D2B]/10 text-[#895D2B] px-2 py-0.5 rounded">{emp.erp}</span>}
                      {emp.crm && <span className="text-xs bg-[#90533C]/10 text-[#90533C] px-2 py-0.5 rounded">{emp.crm}</span>}
                    </div>
                  </div>
                  {selectedEmpresa?.id === emp.id && <CheckCircleIcon className="h-6 w-6 text-[#A3966A] flex-shrink-0" />}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {empresas.length === 0 && !loading && !showForm && (
          <Card className="text-center py-12">
            <CardContent>
              <BuildingIcon className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <h3 className="text-lg font-semibold mb-2">{t('empresa.noCompany')}</h3>
              <p className="text-muted-foreground mb-4">{t('empresa.createFirst')}</p>
              <Button onClick={() => setShowForm(true)} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                <PlusIcon className="h-4 w-4 mr-2" />
                {t('empresa.save')}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Create Form */}
        {showForm && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BuildingIcon className="h-5 w-5 text-[#A3966A]" />
                {t('empresa.save')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>{t('empresa.name')} *</Label>
                  <Input value={form.nome_empresa} onChange={(e) => setForm({ ...form, nome_empresa: e.target.value })} placeholder="Minha Loja Fashion" />
                </div>
                <div>
                  <Label>{t('empresa.email')} *</Label>
                  <Input type="email" value={form.email_admin} onChange={(e) => setForm({ ...form, email_admin: e.target.value })} placeholder="admin@minhaloja.com" />
                </div>
                <div>
                  <Label>{t('empresa.platform')}</Label>
                  <Input value={form.plataforma_ecommerce} onChange={(e) => setForm({ ...form, plataforma_ecommerce: e.target.value })} placeholder="Shopify, WooCommerce, VTEX..." />
                </div>
                <div>
                  <Label>{t('empresa.erp')}</Label>
                  <Input value={form.erp} onChange={(e) => setForm({ ...form, erp: e.target.value })} placeholder="Bling, Tiny, SAP..." />
                </div>
                <div>
                  <Label>{t('empresa.crm')}</Label>
                  <Input value={form.crm} onChange={(e) => setForm({ ...form, crm: e.target.value })} placeholder="HubSpot, RD Station..." />
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <Button onClick={handleSave} disabled={saving} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                  {saving ? t('common.loading') : t('empresa.save')}
                </Button>
                <Button variant="outline" onClick={() => setShowForm(false)}>{t('common.cancel')}</Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}