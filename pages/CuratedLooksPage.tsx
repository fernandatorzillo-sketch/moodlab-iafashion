import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  PlusIcon, SparklesIcon, Loader2Icon, TrashIcon, EditIcon,
  AlertCircleIcon, BookOpenIcon, TagIcon, XIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

interface CuratedLook {
  id?: number;
  nome: string;
  ocasiao: string;
  estilo: string;
  descricao_editorial: string;
  observacoes_marca: string;
  tags: string;
  prioridade: number;
  ativo: boolean;
  tipo: string;
}

const EMPTY_LOOK: CuratedLook = {
  nome: '', ocasiao: '', estilo: '', descricao_editorial: '',
  observacoes_marca: '', tags: '', prioridade: 1, ativo: true, tipo: 'look',
};

const OCASIOES = ['praia', 'viagem', 'jantar', 'resort', 'trabalho', 'casual', 'festa', 'esporte'];
const ESTILOS = ['casual', 'formal', 'resort', 'editorial', 'streetwear', 'boho', 'minimalista', 'romântico'];
const TIPOS = ['look', 'editorial', 'campanha', 'vitrine'];

export default function CuratedLooksPage() {
  const { language } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();

  const [looks, setLooks] = useState<CuratedLook[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingLook, setEditingLook] = useState<CuratedLook>(EMPTY_LOOK);
  const [saving, setSaving] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => { if (empresa) loadLooks(); }, [empresa]);

  const loadLooks = async () => {
    try {
      const res = await client.entities.curated_looks.query({ query: { empresa_id: empresa!.id }, sort: '-prioridade', limit: 100 });
      setLooks(res.data?.items || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleSave = async () => {
    if (!empresa || !editingLook.nome) return;
    setSaving(true);
    try {
      if (editingLook.id) {
        await client.entities.curated_looks.update({ id: String(editingLook.id), data: { ...editingLook, empresa_id: empresa.id } });
        toast.success(language === 'pt' ? 'Look atualizado!' : 'Look updated!');
      } else {
        await client.entities.curated_looks.create({ data: { ...editingLook, empresa_id: empresa.id, created_at: new Date().toISOString() } });
        toast.success(language === 'pt' ? 'Look criado!' : 'Look created!');
      }
      setShowForm(false);
      setEditingLook(EMPTY_LOOK);
      loadLooks();
    } catch (err) { console.error(err); toast.error('Failed to save'); }
    finally { setSaving(false); }
  };

  const handleDelete = async (id: number) => {
    try {
      await client.entities.curated_looks.delete({ id: String(id) });
      toast.success(language === 'pt' ? 'Look removido!' : 'Look deleted!');
      loadLooks();
    } catch (err) { console.error(err); toast.error('Failed to delete'); }
  };

  const startEdit = (look: CuratedLook) => {
    setEditingLook(look);
    setShowForm(true);
  };

  const filteredLooks = filterType === 'all' ? looks : looks.filter((l) => l.tipo === filterType);

  if (!empresa) {
    return (
      <div className="min-h-screen bg-background"><Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <AlertCircleIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{language === 'pt' ? 'Cadastre uma empresa primeiro' : 'Register a company first'}</h2>
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
              {language === 'pt' ? 'Biblioteca de Looks' : 'Look Library'}
            </h1>
            <p className="text-muted-foreground">
              {language === 'pt' ? 'Curadoria de looks, editoriais e campanhas para treinar a IA' : 'Curate looks, editorials and campaigns to train AI'}
            </p>
            <Badge className="mt-2 bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10">{empresa.nome_empresa}</Badge>
          </div>
          <Button onClick={() => { setEditingLook(EMPTY_LOOK); setShowForm(true); }} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
            <PlusIcon className="h-4 w-4 mr-2" />
            {language === 'pt' ? 'Novo Look' : 'New Look'}
          </Button>
        </div>

        {/* Filter */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {['all', ...TIPOS].map((tipo) => (
            <button key={tipo} onClick={() => setFilterType(tipo)} className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${filterType === tipo ? 'bg-[#A3966A] text-white border-[#A3966A]' : 'border-border hover:border-[#A3966A]'}`}>
              {tipo === 'all' ? (language === 'pt' ? 'Todos' : 'All') : tipo}
            </button>
          ))}
          <Badge variant="secondary" className="ml-auto">{filteredLooks.length} looks</Badge>
        </div>

        {/* Form Modal */}
        {showForm && (
          <Card className="mb-6 border-[#A3966A]/30">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <SparklesIcon className="h-5 w-5 text-[#A3966A]" />
                  {editingLook.id ? (language === 'pt' ? 'Editar Look' : 'Edit Look') : (language === 'pt' ? 'Novo Look' : 'New Look')}
                </CardTitle>
                <Button variant="ghost" size="icon" onClick={() => setShowForm(false)}><XIcon className="h-4 w-4" /></Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>{language === 'pt' ? 'Nome do Look' : 'Look Name'}</Label>
                  <Input value={editingLook.nome} onChange={(e) => setEditingLook({ ...editingLook, nome: e.target.value })} placeholder={language === 'pt' ? 'Ex: Resort Sunset' : 'Ex: Resort Sunset'} className="mt-1" />
                </div>
                <div>
                  <Label>{language === 'pt' ? 'Tipo' : 'Type'}</Label>
                  <select value={editingLook.tipo} onChange={(e) => setEditingLook({ ...editingLook, tipo: e.target.value })} className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background mt-1">
                    {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>{language === 'pt' ? 'Ocasião' : 'Occasion'}</Label>
                  <select value={editingLook.ocasiao} onChange={(e) => setEditingLook({ ...editingLook, ocasiao: e.target.value })} className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background mt-1">
                    <option value="">-</option>
                    {OCASIOES.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
                <div>
                  <Label>{language === 'pt' ? 'Estilo' : 'Style'}</Label>
                  <select value={editingLook.estilo} onChange={(e) => setEditingLook({ ...editingLook, estilo: e.target.value })} className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background mt-1">
                    <option value="">-</option>
                    {ESTILOS.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <Label>{language === 'pt' ? 'Descrição Editorial' : 'Editorial Description'}</Label>
                <Textarea value={editingLook.descricao_editorial} onChange={(e) => setEditingLook({ ...editingLook, descricao_editorial: e.target.value })} rows={3} className="mt-1" placeholder={language === 'pt' ? 'Descreva o look com linguagem editorial...' : 'Describe the look with editorial language...'} />
              </div>
              <div>
                <Label>{language === 'pt' ? 'Observações da Marca' : 'Brand Notes'}</Label>
                <Textarea value={editingLook.observacoes_marca} onChange={(e) => setEditingLook({ ...editingLook, observacoes_marca: e.target.value })} rows={2} className="mt-1" placeholder={language === 'pt' ? 'Notas internas sobre este look...' : 'Internal notes about this look...'} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Tags</Label>
                  <Input value={editingLook.tags} onChange={(e) => setEditingLook({ ...editingLook, tags: e.target.value })} placeholder="resort, verão, elegante" className="mt-1" />
                </div>
                <div>
                  <Label>{language === 'pt' ? 'Prioridade (1-10)' : 'Priority (1-10)'}</Label>
                  <Input type="number" min={1} max={10} value={editingLook.prioridade} onChange={(e) => setEditingLook({ ...editingLook, prioridade: parseInt(e.target.value) || 1 })} className="mt-1" />
                </div>
              </div>
              <div className="flex gap-3">
                <Button onClick={handleSave} disabled={saving || !editingLook.nome} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                  {saving ? <Loader2Icon className="h-4 w-4 mr-2 animate-spin" /> : <SparklesIcon className="h-4 w-4 mr-2" />}
                  {language === 'pt' ? 'Salvar' : 'Save'}
                </Button>
                <Button variant="outline" onClick={() => setShowForm(false)}>{language === 'pt' ? 'Cancelar' : 'Cancel'}</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Looks Grid */}
        {loading ? (
          <div className="flex justify-center py-12"><Loader2Icon className="h-8 w-8 animate-spin text-[#A3966A]" /></div>
        ) : filteredLooks.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <BookOpenIcon className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-bold mb-2">{language === 'pt' ? 'Nenhum look cadastrado' : 'No looks registered'}</h3>
              <p className="text-muted-foreground mb-4">{language === 'pt' ? 'Crie looks curados para treinar a IA da sua marca' : 'Create curated looks to train your brand AI'}</p>
              <Button onClick={() => { setEditingLook(EMPTY_LOOK); setShowForm(true); }} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                <PlusIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Criar Primeiro Look' : 'Create First Look'}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredLooks.map((look) => (
              <Card key={look.id} className="group hover:shadow-lg transition-all">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-bold text-foreground">{look.nome}</h3>
                      <div className="flex gap-1.5 mt-1">
                        <Badge variant="secondary" className="text-xs">{look.tipo}</Badge>
                        {look.ocasiao && <Badge variant="outline" className="text-xs">{look.ocasiao}</Badge>}
                        {look.estilo && <Badge variant="outline" className="text-xs">{look.estilo}</Badge>}
                      </div>
                    </div>
                    <Badge className={`text-xs ${look.ativo ? 'bg-green-100 text-green-700 hover:bg-green-100' : 'bg-red-100 text-red-700 hover:bg-red-100'}`}>
                      {look.ativo ? (language === 'pt' ? 'Ativo' : 'Active') : (language === 'pt' ? 'Inativo' : 'Inactive')}
                    </Badge>
                  </div>
                  {look.descricao_editorial && <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{look.descricao_editorial}</p>}
                  {look.tags && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {look.tags.split(',').map((tag, i) => (
                        <span key={i} className="inline-flex items-center gap-0.5 text-xs bg-[#A3966A]/10 text-[#A3966A] px-2 py-0.5 rounded-full">
                          <TagIcon className="h-3 w-3" />{tag.trim()}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button size="sm" variant="outline" onClick={() => startEdit(look)}><EditIcon className="h-3 w-3 mr-1" />{language === 'pt' ? 'Editar' : 'Edit'}</Button>
                    <Button size="sm" variant="outline" className="text-red-500 hover:text-red-700" onClick={() => look.id && handleDelete(look.id)}><TrashIcon className="h-3 w-3" /></Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}