import { useState, useRef } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  UploadIcon, FileSpreadsheetIcon, ArrowRightIcon, CheckCircleIcon,
  AlertCircleIcon, RefreshCwIcon, PlugIcon, MapPinIcon, Loader2Icon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

type EntityType = 'clientes' | 'produtos' | 'pedidos' | 'itens_pedido';

const ENTITY_FIELDS: Record<EntityType, string[]> = {
  clientes: ['nome', 'email', 'telefone', 'genero', 'cidade', 'estado', 'data_cadastro', 'estilo_resumo', 'tamanho_top', 'tamanho_bottom', 'tamanho_dress'],
  produtos: ['sku', 'nome', 'categoria', 'subcategoria', 'colecao', 'cor', 'modelagem', 'tamanho', 'preco', 'estoque', 'imagem_url', 'link_produto', 'ocasiao', 'tags_estilo', 'ativo'],
  pedidos: ['cliente_id', 'numero_pedido', 'data_pedido', 'valor_total', 'status'],
  itens_pedido: ['pedido_id', 'produto_id', 'sku', 'quantidade', 'preco_unitario', 'tamanho'],
};

type Step = 'select' | 'upload' | 'mapping' | 'preview' | 'result';

export default function ImportPage() {
  const { t } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>('select');
  const [entityType, setEntityType] = useState<EntityType | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<Record<string, string>[]>([]);
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({});
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ success: number; errors: string[] } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<'csv' | 'api'>('csv');
  const [apiForm, setApiForm] = useState({ url: '', apiKey: '' });

  const parseCsv = (text: string) => {
    const lines = text.split('\n').filter((l) => l.trim());
    if (lines.length < 2) { toast.error('CSV must have header + data rows'); return; }

    // Detect separator
    const sep = lines[0].includes(';') ? ';' : ',';
    const headers = lines[0].split(sep).map((h) => h.trim().replace(/^"|"$/g, ''));
    const rows: Record<string, string>[] = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(sep).map((v) => v.trim().replace(/^"|"$/g, ''));
      const row: Record<string, string> = {};
      headers.forEach((h, idx) => { row[h] = values[idx] || ''; });
      rows.push(row);
    }

    setCsvHeaders(headers);
    setCsvRows(rows);

    // Auto-map matching fields
    if (entityType) {
      const dbFields = ENTITY_FIELDS[entityType];
      const autoMap: Record<string, string> = {};
      headers.forEach((h) => {
        const normalized = h.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const match = dbFields.find((f) => f === normalized || f.includes(normalized) || normalized.includes(f));
        if (match) autoMap[h] = match;
      });
      setFieldMapping(autoMap);
    }

    setStep('mapping');
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      parseCsv(text);
    };
    reader.readAsText(file, 'UTF-8');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => parseCsv(ev.target?.result as string);
    reader.readAsText(file, 'UTF-8');
  };

  const updateMapping = (csvCol: string, dbField: string) => {
    setFieldMapping((prev) => {
      const next = { ...prev };
      if (dbField === '') delete next[csvCol];
      else next[csvCol] = dbField;
      return next;
    });
  };

  const validationStats = () => {
    const mapped = Object.keys(fieldMapping).length;
    const total = csvHeaders.length;
    return { mapped, total, valid: mapped > 0 };
  };

  const handleImport = async () => {
    if (!empresa || !entityType) return;
    setImporting(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/import/process-csv',
        method: 'POST',
        data: {
          empresa_id: empresa.id,
          entity_type: entityType,
          field_mapping: fieldMapping,
          rows: csvRows,
        },
      });
      setImportResult(res.data);
      setStep('result');
      if (res.data.success > 0) toast.success(`${res.data.success} ${t('import.success')}`);
      if (res.data.errors?.length > 0) toast.error(`${res.data.errors.length} ${t('import.errors')}`);
    } catch (err) {
      console.error(err);
      toast.error('Import failed');
    } finally {
      setImporting(false);
    }
  };

  const handleSyncCloset = async () => {
    if (!empresa) return;
    setSyncing(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/import/sync-closet',
        method: 'POST',
        data: { empresa_id: empresa.id },
      });
      toast.success(`${res.data.new_entries} ${t('import.syncDone')}`);
    } catch (err) {
      console.error(err);
      toast.error('Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const resetImport = () => {
    setStep('select');
    setEntityType(null);
    setCsvHeaders([]);
    setCsvRows([]);
    setFieldMapping({});
    setImportResult(null);
  };

  if (!empresa) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <AlertCircleIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('import.noEmpresa')}</h2>
          <Button onClick={() => navigate('/empresa')} className="bg-[#A3966A] hover:bg-[#895D2B] text-white mt-4">
            {t('empresa.title')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('import.title')}</h1>
          <p className="text-muted-foreground">{t('import.subtitle')}</p>
          <Badge className="mt-2 bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10">{empresa.nome_empresa}</Badge>
        </div>

        {/* Tab Selector */}
        <div className="flex gap-2 mb-6">
          <Button variant={activeTab === 'csv' ? 'default' : 'outline'} onClick={() => setActiveTab('csv')} className={activeTab === 'csv' ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white' : ''}>
            <FileSpreadsheetIcon className="h-4 w-4 mr-2" />
            {t('import.csv')}
          </Button>
          <Button variant={activeTab === 'api' ? 'default' : 'outline'} onClick={() => setActiveTab('api')} className={activeTab === 'api' ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white' : ''}>
            <PlugIcon className="h-4 w-4 mr-2" />
            {t('import.api')}
          </Button>
        </div>

        {activeTab === 'api' && (
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><PlugIcon className="h-5 w-5 text-[#A3966A]" />{t('import.api')}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{t('import.apiUrl')}</Label>
                <Input value={apiForm.url} onChange={(e) => setApiForm({ ...apiForm, url: e.target.value })} placeholder="https://api.minhaloja.com/v1/products" />
              </div>
              <div>
                <Label>{t('import.apiKey')}</Label>
                <Input type="password" value={apiForm.apiKey} onChange={(e) => setApiForm({ ...apiForm, apiKey: e.target.value })} placeholder="sk_live_..." />
              </div>
              <Button className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                <PlugIcon className="h-4 w-4 mr-2" />
                {t('import.testConnection')}
              </Button>
              <p className="text-sm text-muted-foreground">API integration coming soon. Use CSV import for now.</p>
            </CardContent>
          </Card>
        )}

        {activeTab === 'csv' && (
          <>
            {/* Step 1: Select Entity */}
            {step === 'select' && (
              <Card>
                <CardHeader><CardTitle>{t('import.selectEntity')}</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {(Object.keys(ENTITY_FIELDS) as EntityType[]).map((entity) => (
                      <button
                        key={entity}
                        onClick={() => { setEntityType(entity); setStep('upload'); }}
                        className="p-4 rounded-xl border-2 border-border hover:border-[#A3966A] transition-all text-center"
                      >
                        <FileSpreadsheetIcon className="h-8 w-8 text-[#A3966A] mx-auto mb-2" />
                        <span className="font-medium capitalize">{t(`import.${entity}`)}</span>
                        <p className="text-xs text-muted-foreground mt-1">{ENTITY_FIELDS[entity].length} fields</p>
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Step 2: Upload CSV */}
            {step === 'upload' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <UploadIcon className="h-5 w-5 text-[#A3966A]" />
                    {t('import.uploadCsv')} — <span className="capitalize">{entityType && t(`import.${entityType}`)}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-[#A3966A]/30 rounded-xl p-12 text-center cursor-pointer hover:border-[#A3966A] transition-colors"
                  >
                    <UploadIcon className="h-12 w-12 text-[#A3966A]/50 mx-auto mb-4" />
                    <p className="text-lg font-medium text-foreground mb-1">{t('import.dragDrop')}</p>
                    <p className="text-sm text-muted-foreground">.csv, .txt</p>
                    <input ref={fileInputRef} type="file" accept=".csv,.txt" className="hidden" onChange={handleFileUpload} />
                  </div>
                  <Button variant="outline" onClick={() => setStep('select')} className="mt-4">{t('common.cancel')}</Button>
                </CardContent>
              </Card>
            )}

            {/* Step 3: Field Mapping */}
            {step === 'mapping' && entityType && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MapPinIcon className="h-5 w-5 text-[#A3966A]" />
                      {t('import.mapping')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {csvHeaders.map((header) => (
                        <div key={header} className="flex items-center gap-4">
                          <div className="w-1/3">
                            <span className="text-sm font-medium bg-muted px-3 py-1.5 rounded">{header}</span>
                          </div>
                          <ArrowRightIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <div className="w-1/3">
                            <select
                              value={fieldMapping[header] || ''}
                              onChange={(e) => updateMapping(header, e.target.value)}
                              className="w-full border border-border rounded-md px-3 py-1.5 text-sm bg-background"
                            >
                              <option value="">{t('import.ignore')}</option>
                              {ENTITY_FIELDS[entityType].map((field) => (
                                <option key={field} value={field}>{field}</option>
                              ))}
                            </select>
                          </div>
                          <div className="w-16">
                            {fieldMapping[header] ? (
                              <CheckCircleIcon className="h-5 w-5 text-green-500" />
                            ) : (
                              <AlertCircleIcon className="h-5 w-5 text-muted-foreground" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Validation & Preview */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      {t('import.validation')}
                      <Badge variant="secondary">{csvRows.length} {t('import.rowsFound')}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 mb-4">
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                        {validationStats().mapped}/{validationStats().total} {t('import.mapping')}
                      </Badge>
                    </div>
                    {/* Preview Table */}
                    <div className="overflow-x-auto max-h-64 border rounded-lg">
                      <table className="w-full text-sm">
                        <thead className="bg-muted sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left font-medium">#</th>
                            {Object.values(fieldMapping).map((field) => (
                              <th key={field} className="px-3 py-2 text-left font-medium">{field}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {csvRows.slice(0, 5).map((row, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="px-3 py-2 text-muted-foreground">{idx + 1}</td>
                              {Object.entries(fieldMapping).map(([csvCol, dbField]) => (
                                <td key={dbField} className="px-3 py-2">{row[csvCol] || '-'}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="flex gap-3 mt-4">
                      <Button
                        onClick={handleImport}
                        disabled={importing || !validationStats().valid}
                        className="bg-[#A3966A] hover:bg-[#895D2B] text-white"
                      >
                        {importing ? <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" />{t('import.importing')}</> : t('import.startImport')}
                      </Button>
                      <Button variant="outline" onClick={() => setStep('upload')}>{t('common.cancel')}</Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Step 4: Result */}
            {step === 'result' && importResult && (
              <Card>
                <CardContent className="p-8 text-center">
                  <CheckCircleIcon className="h-16 w-16 text-green-500 mx-auto mb-4" />
                  <h3 className="text-2xl font-bold mb-2">{importResult.success} {t('import.success')}</h3>
                  {importResult.errors.length > 0 && (
                    <div className="mt-4 text-left max-h-40 overflow-y-auto bg-red-50 rounded-lg p-4">
                      <p className="font-medium text-red-700 mb-2">{importResult.errors.length} {t('import.errors')}:</p>
                      {importResult.errors.slice(0, 10).map((err, i) => (
                        <p key={i} className="text-sm text-red-600">{err}</p>
                      ))}
                    </div>
                  )}
                  <div className="flex gap-3 justify-center mt-6">
                    <Button onClick={resetImport} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                      <RefreshCwIcon className="h-4 w-4 mr-2" />
                      {t('import.csv')}
                    </Button>
                    <Button variant="outline" onClick={handleSyncCloset} disabled={syncing}>
                      {syncing ? <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" />{t('import.syncing')}</> : t('import.syncCloset')}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Closet Sync Card */}
        {activeTab === 'csv' && step === 'select' && (
          <Card className="mt-6">
            <CardContent className="p-6 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-foreground">{t('import.syncCloset')}</h3>
                <p className="text-sm text-muted-foreground">Auto-populate customer closets from completed orders</p>
              </div>
              <Button onClick={handleSyncCloset} disabled={syncing} variant="outline" className="border-[#A3966A] text-[#A3966A]">
                {syncing ? <Loader2Icon className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCwIcon className="h-4 w-4 mr-2" />}
                {syncing ? t('import.syncing') : 'Sync'}
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}