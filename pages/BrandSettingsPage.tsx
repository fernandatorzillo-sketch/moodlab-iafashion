import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  PaletteIcon, TypeIcon, LayoutIcon, SaveIcon, Loader2Icon,
  EyeIcon, AlertCircleIcon, SparklesIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

interface BrandSettings {
  id?: number;
  logo_url: string;
  brand_name: string;
  primary_color: string;
  secondary_color: string;
  background_color: string;
  text_color: string;
  font_family: string;
  button_style: string;
  border_radius: string;
  display_mode: string;
  tone_of_voice: string;
  aesthetic_description: string;
  module_name_closet: string;
  module_name_looks: string;
  module_name_recommendations: string;
  banner_url: string;
}

const DEFAULT_SETTINGS: BrandSettings = {
  logo_url: '',
  brand_name: '',
  primary_color: '#A3966A',
  secondary_color: '#895D2B',
  background_color: '#FFFFFF',
  text_color: '#1A1A1A',
  font_family: 'DM Sans',
  button_style: 'rounded',
  border_radius: '12px',
  display_mode: 'premium',
  tone_of_voice: '',
  aesthetic_description: '',
  module_name_closet: 'Seu Closet',
  module_name_looks: 'Monte seu Look',
  module_name_recommendations: 'Combina com Você',
  banner_url: '',
};

const FONT_OPTIONS = ['DM Sans', 'Inter', 'Playfair Display', 'Montserrat', 'Roboto', 'Lora', 'Poppins', 'Raleway'];
const BUTTON_STYLES = ['rounded', 'square', 'pill'];
const DISPLAY_MODES = ['minimal', 'premium', 'editorial'];
const AESTHETICS = [
  'Resort sofisticado', 'Feminino contemporâneo', 'Casual chic', 'Minimalista',
  'Tropical elegante', 'Moda autoral', 'Lifestyle premium', 'Streetwear moderno',
  'Boho chic', 'Clássico atemporal',
];

export default function BrandSettingsPage() {
  const { t, language } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();
  const [settings, setSettings] = useState<BrandSettings>(DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (empresa) loadSettings();
  }, [empresa]);

  const loadSettings = async () => {
    try {
      const res = await client.entities.brand_settings.query({ query: { empresa_id: empresa!.id }, limit: 1 });
      if (res.data?.items?.length > 0) {
        const s = res.data.items[0];
        setSettings({ ...DEFAULT_SETTINGS, ...s });
      }
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSave = async () => {
    if (!empresa) return;
    setSaving(true);
    try {
      if (settings.id) {
        await client.entities.brand_settings.update({ id: String(settings.id), data: { ...settings, empresa_id: empresa.id } });
      } else {
        const res = await client.entities.brand_settings.create({ data: { ...settings, empresa_id: empresa.id } });
        if (res.data) setSettings({ ...settings, id: res.data.id });
      }
      toast.success(language === 'pt' ? 'Configurações salvas!' : 'Settings saved!');
    } catch (err) { console.error(err); toast.error('Failed to save'); }
    finally { setSaving(false); }
  };

  const update = (field: keyof BrandSettings, value: string) => {
    setSettings((prev) => ({ ...prev, [field]: value }));
  };

  if (!empresa) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <AlertCircleIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('import.noEmpresa')}</h2>
          <Button onClick={() => navigate('/empresa')} className="bg-[#A3966A] hover:bg-[#895D2B] text-white mt-4">{t('empresa.title')}</Button>
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
              {language === 'pt' ? 'Identidade Visual' : 'Brand Identity'}
            </h1>
            <p className="text-muted-foreground">
              {language === 'pt' ? 'Personalize a aparência do motor para sua marca' : 'Customize the engine appearance for your brand'}
            </p>
            <Badge className="mt-2 bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10">{empresa.nome_empresa}</Badge>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setShowPreview(!showPreview)}>
              <EyeIcon className="h-4 w-4 mr-2" />
              {language === 'pt' ? 'Preview' : 'Preview'}
            </Button>
            <Button onClick={handleSave} disabled={saving} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
              {saving ? <Loader2Icon className="h-4 w-4 mr-2 animate-spin" /> : <SaveIcon className="h-4 w-4 mr-2" />}
              {language === 'pt' ? 'Salvar' : 'Save'}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Colors */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><PaletteIcon className="h-5 w-5 text-[#A3966A]" />{language === 'pt' ? 'Cores' : 'Colors'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {[
                  { key: 'primary_color' as const, label: language === 'pt' ? 'Cor Primária' : 'Primary Color' },
                  { key: 'secondary_color' as const, label: language === 'pt' ? 'Cor Secundária' : 'Secondary Color' },
                  { key: 'background_color' as const, label: language === 'pt' ? 'Fundo' : 'Background' },
                  { key: 'text_color' as const, label: language === 'pt' ? 'Texto' : 'Text' },
                ].map((item) => (
                  <div key={item.key}>
                    <Label className="text-xs">{item.label}</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <input type="color" value={settings[item.key]} onChange={(e) => update(item.key, e.target.value)} className="w-10 h-10 rounded cursor-pointer border" />
                      <Input value={settings[item.key]} onChange={(e) => update(item.key, e.target.value)} className="font-mono text-sm" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Typography & Style */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><TypeIcon className="h-5 w-5 text-[#A3966A]" />{language === 'pt' ? 'Tipografia & Estilo' : 'Typography & Style'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{language === 'pt' ? 'Família de Fonte' : 'Font Family'}</Label>
                <select value={settings.font_family} onChange={(e) => update('font_family', e.target.value)} className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background mt-1">
                  {FONT_OPTIONS.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>{language === 'pt' ? 'Estilo de Botão' : 'Button Style'}</Label>
                  <select value={settings.button_style} onChange={(e) => update('button_style', e.target.value)} className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background mt-1">
                    {BUTTON_STYLES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <Label>{language === 'pt' ? 'Arredondamento' : 'Border Radius'}</Label>
                  <Input value={settings.border_radius} onChange={(e) => update('border_radius', e.target.value)} placeholder="12px" className="mt-1" />
                </div>
              </div>
              <div>
                <Label>{language === 'pt' ? 'Modo de Exibição' : 'Display Mode'}</Label>
                <div className="flex gap-2 mt-1">
                  {DISPLAY_MODES.map((mode) => (
                    <button key={mode} onClick={() => update('display_mode', mode)} className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${settings.display_mode === mode ? 'bg-[#A3966A] text-white border-[#A3966A]' : 'border-border hover:border-[#A3966A]'}`}>
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Brand Identity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><SparklesIcon className="h-5 w-5 text-[#A3966A]" />{language === 'pt' ? 'Identidade da Marca' : 'Brand Identity'}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{language === 'pt' ? 'Nome Exibido' : 'Display Name'}</Label>
                <Input value={settings.brand_name} onChange={(e) => update('brand_name', e.target.value)} placeholder={empresa.nome_empresa} className="mt-1" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'URL do Logo' : 'Logo URL'}</Label>
                <Input value={settings.logo_url} onChange={(e) => update('logo_url', e.target.value)} placeholder="https://..." className="mt-1" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'Estética da Marca' : 'Brand Aesthetic'}</Label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {AESTHETICS.map((a) => (
                    <button key={a} onClick={() => update('aesthetic_description', a)} className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${settings.aesthetic_description === a ? 'bg-[#A3966A] text-white border-[#A3966A]' : 'border-border hover:border-[#A3966A]'}`}>
                      {a}
                    </button>
                  ))}
                </div>
                <Input value={settings.aesthetic_description} onChange={(e) => update('aesthetic_description', e.target.value)} placeholder={language === 'pt' ? 'Ou descreva livremente...' : 'Or describe freely...'} className="mt-2" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'Tom de Voz' : 'Tone of Voice'}</Label>
                <Textarea value={settings.tone_of_voice} onChange={(e) => update('tone_of_voice', e.target.value)} placeholder={language === 'pt' ? 'Ex: Sofisticado e acolhedor, com linguagem que inspira confiança...' : 'Ex: Sophisticated and welcoming, with language that inspires confidence...'} className="mt-1" rows={3} />
              </div>
            </CardContent>
          </Card>

          {/* Module Names */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><LayoutIcon className="h-5 w-5 text-[#A3966A]" />{language === 'pt' ? 'Nomes dos Módulos' : 'Module Names'}</CardTitle>
              <CardDescription>{language === 'pt' ? 'Personalize os nomes exibidos ao cliente final' : 'Customize names shown to end customers'}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{language === 'pt' ? 'Módulo Closet' : 'Closet Module'}</Label>
                <Input value={settings.module_name_closet} onChange={(e) => update('module_name_closet', e.target.value)} placeholder="Seu Closet" className="mt-1" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'Módulo Looks' : 'Looks Module'}</Label>
                <Input value={settings.module_name_looks} onChange={(e) => update('module_name_looks', e.target.value)} placeholder="Monte seu Look" className="mt-1" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'Módulo Recomendações' : 'Recommendations Module'}</Label>
                <Input value={settings.module_name_recommendations} onChange={(e) => update('module_name_recommendations', e.target.value)} placeholder="Combina com Você" className="mt-1" />
              </div>
              <div>
                <Label>{language === 'pt' ? 'URL do Banner' : 'Banner URL'}</Label>
                <Input value={settings.banner_url} onChange={(e) => update('banner_url', e.target.value)} placeholder="https://..." className="mt-1" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Live Preview */}
        {showPreview && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>{language === 'pt' ? 'Pré-visualização' : 'Preview'}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="rounded-xl overflow-hidden border" style={{ backgroundColor: settings.background_color, color: settings.text_color, fontFamily: settings.font_family }}>
                {settings.banner_url && <img src={settings.banner_url} alt="Banner" className="w-full h-32 object-cover" />}
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    {settings.logo_url && <img src={settings.logo_url} alt="Logo" className="h-10 w-10 rounded-full object-cover" />}
                    <h2 className="text-xl font-bold">{settings.brand_name || empresa.nome_empresa}</h2>
                  </div>
                  <div className="flex gap-3 mb-4">
                    {[settings.module_name_closet, settings.module_name_looks, settings.module_name_recommendations].map((name) => (
                      <button key={name} style={{
                        backgroundColor: settings.primary_color, color: '#fff',
                        borderRadius: settings.button_style === 'pill' ? '999px' : settings.button_style === 'square' ? '0' : settings.border_radius,
                        padding: '8px 16px', fontSize: '14px', fontWeight: 500,
                      }}>
                        {name}
                      </button>
                    ))}
                  </div>
                  <p className="text-sm opacity-70">{language === 'pt' ? `Estética: ${settings.aesthetic_description || 'Não definida'}` : `Aesthetic: ${settings.aesthetic_description || 'Not set'}`}</p>
                  <p className="text-sm opacity-70 mt-1">{language === 'pt' ? `Modo: ${settings.display_mode}` : `Mode: ${settings.display_mode}`}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}