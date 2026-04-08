import { useState, useRef } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  UploadIcon, FileSpreadsheetIcon, ArrowRightIcon, CheckCircleIcon,
  AlertCircleIcon, RefreshCwIcon, MapPinIcon, Loader2Icon,
  ArrowLeftIcon, ShirtIcon, PlugZapIcon, LinkIcon, ExternalLinkIcon,
  DownloadIcon, FileTextIcon, InfoIcon, AlertTriangleIcon, XCircleIcon,
  BrainIcon, SparklesIcon, WandIcon, ZapIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';
import { useNavigate } from 'react-router-dom';

type EntityType = 'clientes' | 'produtos' | 'pedidos' | 'itens_pedido';
type IntegrationId = 'csv' | 'smart' | 'vtex' | 'shopify' | 'dito' | 'selbie';
type CsvStep = 'entity' | 'upload' | 'detection' | 'mapping' | 'result';

const ENTITY_FIELDS: Record<EntityType, string[]> = {
  clientes: ['nome', 'email', 'telefone', 'genero', 'cidade', 'estado', 'data_cadastro', 'estilo_resumo', 'tamanho_top', 'tamanho_bottom', 'tamanho_dress'],
  produtos: ['sku', 'nome', 'categoria', 'subcategoria', 'colecao', 'cor', 'modelagem', 'tamanho', 'preco', 'estoque', 'imagem_url', 'link_produto', 'ocasiao', 'tags_estilo', 'ativo'],
  pedidos: ['cliente_id', 'numero_pedido', 'data_pedido', 'valor_total', 'status'],
  itens_pedido: ['pedido_id', 'produto_id', 'sku', 'quantidade', 'preco_unitario', 'tamanho'],
};

const REQUIRED_FIELDS: Record<EntityType, string[]> = {
  produtos: ['sku', 'nome'],
  clientes: ['nome'],
  pedidos: ['numero_pedido', 'data_pedido', 'valor_total', 'status'],
  itens_pedido: ['pedido_id', 'sku', 'quantidade'],
};

// ============================================================
// SYNONYM DICTIONARY — maps common ERP/CRM/e-commerce column
// names (lowercased, stripped of accents & special chars) to
// internal MoodLab field names, grouped by entity.
// ============================================================
const SYNONYM_MAP: Record<string, { field: string; entities: EntityType[] }> = {
  // --- SKU / product code ---
  sku: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  codigo: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  cod_produto: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  codigo_produto: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  referencia: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  ref: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  item_code: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  product_code: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  cod_ref: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  referencia_produto: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  cod_item: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  cod_barras: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  ean: { field: 'sku', entities: ['produtos', 'itens_pedido'] },
  // --- Product name ---
  nome: { field: 'nome', entities: ['produtos', 'clientes'] },
  nome_produto: { field: 'nome', entities: ['produtos'] },
  descricao: { field: 'nome', entities: ['produtos'] },
  descricao_produto: { field: 'nome', entities: ['produtos'] },
  produto: { field: 'nome', entities: ['produtos'] },
  item_name: { field: 'nome', entities: ['produtos'] },
  product_name: { field: 'nome', entities: ['produtos'] },
  titulo: { field: 'nome', entities: ['produtos'] },
  title: { field: 'nome', entities: ['produtos'] },
  name: { field: 'nome', entities: ['produtos', 'clientes'] },
  // --- Customer name ---
  nome_cliente: { field: 'nome', entities: ['clientes'] },
  customer_name: { field: 'nome', entities: ['clientes'] },
  cliente: { field: 'nome', entities: ['clientes'] },
  nome_completo: { field: 'nome', entities: ['clientes'] },
  full_name: { field: 'nome', entities: ['clientes'] },
  // --- Price ---
  preco: { field: 'preco', entities: ['produtos'] },
  valor: { field: 'preco', entities: ['produtos'] },
  price: { field: 'preco', entities: ['produtos'] },
  valor_venda: { field: 'preco', entities: ['produtos'] },
  preco_venda: { field: 'preco', entities: ['produtos'] },
  valor_unitario: { field: 'preco', entities: ['produtos'] },
  preco_unitario: { field: 'preco_unitario', entities: ['itens_pedido'] },
  unit_price: { field: 'preco_unitario', entities: ['itens_pedido'] },
  valor_item: { field: 'preco_unitario', entities: ['itens_pedido'] },
  // --- Stock ---
  estoque: { field: 'estoque', entities: ['produtos'] },
  saldo: { field: 'estoque', entities: ['produtos'] },
  qtd_estoque: { field: 'estoque', entities: ['produtos'] },
  inventory: { field: 'estoque', entities: ['produtos'] },
  stock: { field: 'estoque', entities: ['produtos'] },
  quantidade_estoque: { field: 'estoque', entities: ['produtos'] },
  saldo_estoque: { field: 'estoque', entities: ['produtos'] },
  disponivel: { field: 'estoque', entities: ['produtos'] },
  // --- Category ---
  categoria: { field: 'categoria', entities: ['produtos'] },
  category: { field: 'categoria', entities: ['produtos'] },
  tipo: { field: 'categoria', entities: ['produtos'] },
  tipo_produto: { field: 'categoria', entities: ['produtos'] },
  departamento: { field: 'categoria', entities: ['produtos'] },
  department: { field: 'categoria', entities: ['produtos'] },
  grupo: { field: 'categoria', entities: ['produtos'] },
  // --- Subcategory ---
  subcategoria: { field: 'subcategoria', entities: ['produtos'] },
  subcategory: { field: 'subcategoria', entities: ['produtos'] },
  subgrupo: { field: 'subcategoria', entities: ['produtos'] },
  sub_categoria: { field: 'subcategoria', entities: ['produtos'] },
  // --- Collection ---
  colecao: { field: 'colecao', entities: ['produtos'] },
  collection: { field: 'colecao', entities: ['produtos'] },
  linha: { field: 'colecao', entities: ['produtos'] },
  temporada: { field: 'colecao', entities: ['produtos'] },
  season: { field: 'colecao', entities: ['produtos'] },
  // --- Color ---
  cor: { field: 'cor', entities: ['produtos'] },
  color: { field: 'cor', entities: ['produtos'] },
  colour: { field: 'cor', entities: ['produtos'] },
  cor_principal: { field: 'cor', entities: ['produtos'] },
  // --- Size ---
  tamanho: { field: 'tamanho', entities: ['produtos', 'itens_pedido'] },
  size: { field: 'tamanho', entities: ['produtos', 'itens_pedido'] },
  tam: { field: 'tamanho', entities: ['produtos', 'itens_pedido'] },
  grade: { field: 'tamanho', entities: ['produtos', 'itens_pedido'] },
  numeracao: { field: 'tamanho', entities: ['produtos', 'itens_pedido'] },
  // --- Fit / Modelagem ---
  modelagem: { field: 'modelagem', entities: ['produtos'] },
  fit: { field: 'modelagem', entities: ['produtos'] },
  caimento: { field: 'modelagem', entities: ['produtos'] },
  silhueta: { field: 'modelagem', entities: ['produtos'] },
  // --- Image ---
  imagem_url: { field: 'imagem_url', entities: ['produtos'] },
  imagem: { field: 'imagem_url', entities: ['produtos'] },
  image: { field: 'imagem_url', entities: ['produtos'] },
  image_url: { field: 'imagem_url', entities: ['produtos'] },
  foto: { field: 'imagem_url', entities: ['produtos'] },
  foto_url: { field: 'imagem_url', entities: ['produtos'] },
  url_imagem: { field: 'imagem_url', entities: ['produtos'] },
  thumbnail: { field: 'imagem_url', entities: ['produtos'] },
  // --- Product link ---
  link_produto: { field: 'link_produto', entities: ['produtos'] },
  url_produto: { field: 'link_produto', entities: ['produtos'] },
  product_url: { field: 'link_produto', entities: ['produtos'] },
  link: { field: 'link_produto', entities: ['produtos'] },
  url: { field: 'link_produto', entities: ['produtos'] },
  // --- Occasion ---
  ocasiao: { field: 'ocasiao', entities: ['produtos'] },
  occasion: { field: 'ocasiao', entities: ['produtos'] },
  uso: { field: 'ocasiao', entities: ['produtos'] },
  // --- Tags ---
  tags_estilo: { field: 'tags_estilo', entities: ['produtos'] },
  tags: { field: 'tags_estilo', entities: ['produtos'] },
  estilo: { field: 'tags_estilo', entities: ['produtos'] },
  style_tags: { field: 'tags_estilo', entities: ['produtos'] },
  keywords: { field: 'tags_estilo', entities: ['produtos'] },
  // --- Active ---
  ativo: { field: 'ativo', entities: ['produtos'] },
  active: { field: 'ativo', entities: ['produtos'] },
  status_produto: { field: 'ativo', entities: ['produtos'] },
  habilitado: { field: 'ativo', entities: ['produtos'] },
  // --- Email ---
  email: { field: 'email', entities: ['clientes'] },
  e_mail: { field: 'email', entities: ['clientes'] },
  email_cliente: { field: 'email', entities: ['clientes'] },
  // --- Phone ---
  telefone: { field: 'telefone', entities: ['clientes'] },
  phone: { field: 'telefone', entities: ['clientes'] },
  celular: { field: 'telefone', entities: ['clientes'] },
  tel: { field: 'telefone', entities: ['clientes'] },
  fone: { field: 'telefone', entities: ['clientes'] },
  whatsapp: { field: 'telefone', entities: ['clientes'] },
  // --- Gender ---
  genero: { field: 'genero', entities: ['clientes'] },
  gender: { field: 'genero', entities: ['clientes'] },
  sexo: { field: 'genero', entities: ['clientes'] },
  // --- City ---
  cidade: { field: 'cidade', entities: ['clientes'] },
  city: { field: 'cidade', entities: ['clientes'] },
  municipio: { field: 'cidade', entities: ['clientes'] },
  // --- State ---
  estado: { field: 'estado', entities: ['clientes'] },
  state: { field: 'estado', entities: ['clientes'] },
  uf: { field: 'estado', entities: ['clientes'] },
  // --- Registration date ---
  data_cadastro: { field: 'data_cadastro', entities: ['clientes'] },
  dt_cadastro: { field: 'data_cadastro', entities: ['clientes'] },
  registration_date: { field: 'data_cadastro', entities: ['clientes'] },
  created_at: { field: 'data_cadastro', entities: ['clientes'] },
  data_registro: { field: 'data_cadastro', entities: ['clientes'] },
  // --- Sizes (customer) ---
  tamanho_top: { field: 'tamanho_top', entities: ['clientes'] },
  tam_blusa: { field: 'tamanho_top', entities: ['clientes'] },
  tam_camisa: { field: 'tamanho_top', entities: ['clientes'] },
  top_size: { field: 'tamanho_top', entities: ['clientes'] },
  tamanho_bottom: { field: 'tamanho_bottom', entities: ['clientes'] },
  tam_calca: { field: 'tamanho_bottom', entities: ['clientes'] },
  tam_saia: { field: 'tamanho_bottom', entities: ['clientes'] },
  bottom_size: { field: 'tamanho_bottom', entities: ['clientes'] },
  tamanho_dress: { field: 'tamanho_dress', entities: ['clientes'] },
  tam_vestido: { field: 'tamanho_dress', entities: ['clientes'] },
  dress_size: { field: 'tamanho_dress', entities: ['clientes'] },
  // --- Customer external ID ---
  id_cliente_externo: { field: 'cliente_id', entities: ['clientes', 'pedidos'] },
  id_cliente: { field: 'cliente_id', entities: ['pedidos'] },
  cliente_id: { field: 'cliente_id', entities: ['pedidos'] },
  customer_id: { field: 'cliente_id', entities: ['pedidos'] },
  cod_cliente: { field: 'cliente_id', entities: ['pedidos'] },
  cliente_id_externo: { field: 'cliente_id', entities: ['pedidos'] },
  // --- Order number ---
  numero_pedido: { field: 'numero_pedido', entities: ['pedidos'] },
  pedido: { field: 'numero_pedido', entities: ['pedidos'] },
  order_number: { field: 'numero_pedido', entities: ['pedidos'] },
  num_pedido: { field: 'numero_pedido', entities: ['pedidos'] },
  nro_pedido: { field: 'numero_pedido', entities: ['pedidos'] },
  pedido_id: { field: 'numero_pedido', entities: ['pedidos'] },
  pedido_id_externo: { field: 'numero_pedido', entities: ['pedidos'] },
  order_id: { field: 'numero_pedido', entities: ['pedidos'] },
  // --- Order date ---
  data_pedido: { field: 'data_pedido', entities: ['pedidos'] },
  dt_pedido: { field: 'data_pedido', entities: ['pedidos'] },
  order_date: { field: 'data_pedido', entities: ['pedidos'] },
  data_compra: { field: 'data_pedido', entities: ['pedidos'] },
  data_venda: { field: 'data_pedido', entities: ['pedidos'] },
  // --- Order total ---
  valor_total: { field: 'valor_total', entities: ['pedidos'] },
  total: { field: 'valor_total', entities: ['pedidos'] },
  order_total: { field: 'valor_total', entities: ['pedidos'] },
  valor_pedido: { field: 'valor_total', entities: ['pedidos'] },
  subtotal: { field: 'valor_total', entities: ['pedidos'] },
  // --- Order status ---
  status: { field: 'status', entities: ['pedidos'] },
  status_pedido: { field: 'status', entities: ['pedidos'] },
  order_status: { field: 'status', entities: ['pedidos'] },
  situacao: { field: 'status', entities: ['pedidos'] },
  // --- Order item: order reference ---
  pedido_id_externo_item: { field: 'pedido_id', entities: ['itens_pedido'] },
  id_pedido: { field: 'pedido_id', entities: ['itens_pedido'] },
  nr_pedido: { field: 'pedido_id', entities: ['itens_pedido'] },
  // --- Quantity ---
  quantidade: { field: 'quantidade', entities: ['itens_pedido'] },
  qtd: { field: 'quantidade', entities: ['itens_pedido'] },
  qty: { field: 'quantidade', entities: ['itens_pedido'] },
  quantity: { field: 'quantidade', entities: ['itens_pedido'] },
  qtde: { field: 'quantidade', entities: ['itens_pedido'] },
  // --- Product ID (order items) ---
  produto_id: { field: 'produto_id', entities: ['itens_pedido'] },
  id_produto: { field: 'produto_id', entities: ['itens_pedido'] },
  product_id: { field: 'produto_id', entities: ['itens_pedido'] },
};

// Keywords that strongly indicate a specific entity type
const ENTITY_DETECTION_KEYWORDS: Record<EntityType, string[]> = {
  produtos: ['sku', 'codigo', 'referencia', 'ref', 'item_code', 'product_code', 'cod_produto', 'categoria', 'category', 'subcategoria', 'colecao', 'collection', 'modelagem', 'fit', 'estoque', 'stock', 'inventory', 'saldo', 'imagem_url', 'image_url', 'foto', 'link_produto', 'product_url', 'tags_estilo', 'ocasiao', 'cor', 'color'],
  clientes: ['email', 'e_mail', 'telefone', 'phone', 'celular', 'whatsapp', 'genero', 'gender', 'sexo', 'cidade', 'city', 'estado', 'state', 'uf', 'data_cadastro', 'registration_date', 'tamanho_top', 'tamanho_bottom', 'tamanho_dress', 'tam_blusa', 'tam_calca', 'tam_vestido', 'top_size', 'bottom_size', 'dress_size', 'cpf', 'nome_cliente', 'customer_name'],
  pedidos: ['numero_pedido', 'order_number', 'num_pedido', 'nro_pedido', 'pedido_id_externo', 'order_id', 'data_pedido', 'order_date', 'data_compra', 'data_venda', 'valor_total', 'order_total', 'valor_pedido', 'subtotal', 'status_pedido', 'order_status', 'situacao', 'cliente_id_externo', 'id_cliente'],
  itens_pedido: ['quantidade', 'qtd', 'qty', 'quantity', 'qtde', 'preco_unitario', 'unit_price', 'valor_item', 'produto_id', 'id_produto', 'product_id', 'id_pedido', 'nr_pedido'],
};

const CSV_TEMPLATES: Record<EntityType, string> = {
  produtos: 'sku,nome,categoria,subcategoria,colecao,cor,modelagem,tamanho,preco,estoque,imagem_url,link_produto,ocasiao,tags_estilo,ativo',
  clientes: 'id_cliente_externo,nome,email,telefone,cidade,estado,genero,data_cadastro,tamanho_top,tamanho_bottom,tamanho_dress',
  pedidos: 'pedido_id_externo,cliente_id_externo,data_pedido,valor_total,status',
  itens_pedido: 'pedido_id_externo,sku,quantidade,preco_unitario,tamanho',
};

const CSV_EXAMPLES: Record<EntityType, string> = {
  produtos: `sku,nome,categoria,subcategoria,colecao,cor,modelagem,tamanho,preco,estoque,imagem_url,link_produto,ocasiao,tags_estilo,ativo
VES-001,Vestido Midi Floral Resort,vestidos,midi,Verão 2026,estampado floral,evasê,M,389.90,45,https://exemplo.com/img/ves001.jpg,https://exemplo.com/produto/ves001,resort,resort;floral;feminino;elegante,true
CAM-002,Camisa Linho Oversized,camisas,manga longa,Essenciais,branco,oversized,G,259.90,30,https://exemplo.com/img/cam002.jpg,https://exemplo.com/produto/cam002,casual,linho;minimalista;casual;verão,true
SAI-003,Saia Plissada Cetim,saias,midi,Festa 2026,dourado,plissada,P,449.90,15,https://exemplo.com/img/sai003.jpg,https://exemplo.com/produto/sai003,festa,festa;luxo;cetim;dourado,true`,
  clientes: `id_cliente_externo,nome,email,telefone,cidade,estado,genero,data_cadastro,tamanho_top,tamanho_bottom,tamanho_dress
CLI-1001,Ana Beatriz Souza,ana.souza@email.com,(11) 99876-5432,São Paulo,SP,feminino,2024-03-15,M,38,M
CLI-1002,Mariana Costa Lima,mariana.lima@email.com,(21) 98765-4321,Rio de Janeiro,RJ,feminino,2024-06-22,P,36,P
CLI-1003,Carolina Ferreira,carol.ferreira@email.com,(31) 97654-3210,Belo Horizonte,MG,feminino,2025-01-10,G,40,G`,
  pedidos: `pedido_id_externo,cliente_id_externo,data_pedido,valor_total,status
PED-5001,CLI-1001,2025-11-20,649.80,entregue
PED-5002,CLI-1002,2025-12-05,389.90,entregue
PED-5003,CLI-1003,2026-01-15,709.80,enviado`,
  itens_pedido: `pedido_id_externo,sku,quantidade,preco_unitario,tamanho
PED-5001,VES-001,1,389.90,M
PED-5001,CAM-002,1,259.90,G
PED-5002,VES-001,1,389.90,P
PED-5003,SAI-003,1,449.90,P
PED-5003,CAM-002,1,259.90,G`,
};

const FIELD_INSTRUCTIONS: Record<EntityType, Record<string, { pt: string; en: string; required: boolean }>> = {
  produtos: {
    sku: { pt: 'Código único do produto (obrigatório)', en: 'Unique product code (required)', required: true },
    nome: { pt: 'Nome do produto (obrigatório)', en: 'Product name (required)', required: true },
    categoria: { pt: 'Categoria principal: vestidos, camisas, saias, calças...', en: 'Main category: dresses, shirts, skirts, pants...', required: false },
    subcategoria: { pt: 'Subcategoria: midi, longo, curto, manga longa...', en: 'Subcategory: midi, long, short, long sleeve...', required: false },
    colecao: { pt: 'Nome da coleção: Verão 2026, Essenciais...', en: 'Collection name: Summer 2026, Essentials...', required: false },
    cor: { pt: 'Cor principal do produto', en: 'Main product color', required: false },
    modelagem: { pt: 'Tipo de modelagem: evasê, oversized, slim...', en: 'Fit type: flared, oversized, slim...', required: false },
    tamanho: { pt: 'Tamanho: PP, P, M, G, GG ou 34-48', en: 'Size: XS, S, M, L, XL or 34-48', required: false },
    preco: { pt: 'Preço de venda (ex: 389.90)', en: 'Sale price (e.g. 389.90)', required: false },
    estoque: { pt: 'Quantidade em estoque', en: 'Stock quantity', required: false },
    imagem_url: { pt: 'URL da imagem do produto', en: 'Product image URL', required: false },
    link_produto: { pt: 'Link para a página do produto', en: 'Product page link', required: false },
    ocasiao: { pt: 'Ocasião: casual, festa, resort, trabalho...', en: 'Occasion: casual, party, resort, work...', required: false },
    tags_estilo: { pt: 'Tags separadas por ; (ex: resort;floral;elegante)', en: 'Tags separated by ; (e.g. resort;floral;elegant)', required: false },
    ativo: { pt: 'true ou false', en: 'true or false', required: false },
  },
  clientes: {
    id_cliente_externo: { pt: 'ID do cliente no seu sistema (opcional)', en: 'Customer ID in your system (optional)', required: false },
    nome: { pt: 'Nome completo do cliente (obrigatório)', en: 'Customer full name (required)', required: true },
    email: { pt: 'E-mail do cliente', en: 'Customer email', required: false },
    telefone: { pt: 'Telefone com DDD', en: 'Phone with area code', required: false },
    cidade: { pt: 'Cidade do cliente', en: 'Customer city', required: false },
    estado: { pt: 'Estado (sigla: SP, RJ, MG...)', en: 'State abbreviation', required: false },
    genero: { pt: 'feminino, masculino ou outro', en: 'female, male or other', required: false },
    data_cadastro: { pt: 'Data no formato AAAA-MM-DD', en: 'Date in YYYY-MM-DD format', required: false },
    tamanho_top: { pt: 'Tamanho de blusas/camisas: PP, P, M, G, GG', en: 'Top size: XS, S, M, L, XL', required: false },
    tamanho_bottom: { pt: 'Tamanho de calças/saias: 34-48', en: 'Bottom size: 34-48', required: false },
    tamanho_dress: { pt: 'Tamanho de vestidos: PP, P, M, G, GG', en: 'Dress size: XS, S, M, L, XL', required: false },
  },
  pedidos: {
    pedido_id_externo: { pt: 'ID do pedido no seu sistema (obrigatório)', en: 'Order ID in your system (required)', required: true },
    cliente_id_externo: { pt: 'ID do cliente associado ao pedido', en: 'Customer ID associated with the order', required: false },
    data_pedido: { pt: 'Data do pedido AAAA-MM-DD (obrigatório)', en: 'Order date YYYY-MM-DD (required)', required: true },
    valor_total: { pt: 'Valor total do pedido (obrigatório)', en: 'Order total value (required)', required: true },
    status: { pt: 'Status: pendente, pago, enviado, entregue, cancelado (obrigatório)', en: 'Status: pending, paid, shipped, delivered, cancelled (required)', required: true },
  },
  itens_pedido: {
    pedido_id_externo: { pt: 'ID do pedido (obrigatório)', en: 'Order ID (required)', required: true },
    sku: { pt: 'SKU do produto (obrigatório)', en: 'Product SKU (required)', required: true },
    quantidade: { pt: 'Quantidade comprada (obrigatório)', en: 'Quantity purchased (required)', required: true },
    preco_unitario: { pt: 'Preço unitário do item', en: 'Unit price of the item', required: false },
    tamanho: { pt: 'Tamanho comprado', en: 'Size purchased', required: false },
  },
};

interface Integration {
  id: IntegrationId;
  name: string;
  description: { en: string; pt: string };
  icon: string;
  color: string;
  status: 'available' | 'coming_soon';
}

interface ValidationError {
  row: number;
  field: string;
  message: string;
}

interface DetectionResult {
  detectedEntity: EntityType;
  confidence: number;
  scores: Record<EntityType, number>;
  mappedFields: Record<string, string>;
  totalHeaders: number;
  mappedCount: number;
  unmappedHeaders: string[];
}

const INTEGRATIONS: Integration[] = [
  {
    id: 'smart',
    name: 'Importação Inteligente',
    description: {
      en: 'Upload any report from your ERP, CRM or e-commerce — AI auto-detects columns',
      pt: 'Suba qualquer relatório do seu ERP, CRM ou e-commerce — a IA detecta as colunas automaticamente',
    },
    icon: '🧠',
    color: '#A3966A',
    status: 'available',
  },
  {
    id: 'csv',
    name: 'Upload CSV Padrão',
    description: {
      en: 'Import using MoodLab standard CSV templates',
      pt: 'Importe usando os modelos CSV padrão do MoodLab',
    },
    icon: '📄',
    color: '#895D2B',
    status: 'available',
  },
  {
    id: 'vtex',
    name: 'VTEX',
    description: {
      en: 'Connect your VTEX store to sync products, orders, and customers automatically',
      pt: 'Conecte sua loja VTEX para sincronizar produtos, pedidos e clientes automaticamente',
    },
    icon: '🔷',
    color: '#F71963',
    status: 'coming_soon',
  },
  {
    id: 'shopify',
    name: 'Shopify',
    description: {
      en: 'Sync your Shopify store catalog, orders, and customer data',
      pt: 'Sincronize o catálogo, pedidos e dados de clientes da sua loja Shopify',
    },
    icon: '🟢',
    color: '#96BF48',
    status: 'coming_soon',
  },
  {
    id: 'dito',
    name: 'Dito CRM',
    description: {
      en: 'Import customer profiles and purchase history from Dito CRM',
      pt: 'Importe perfis de clientes e histórico de compras do Dito CRM',
    },
    icon: '💜',
    color: '#7B2D8E',
    status: 'coming_soon',
  },
  {
    id: 'selbie',
    name: 'Selbie CRM',
    description: {
      en: 'Connect Selbie CRM to sync customer data and engagement metrics',
      pt: 'Conecte o Selbie CRM para sincronizar dados de clientes e métricas de engajamento',
    },
    icon: '🔵',
    color: '#2563EB',
    status: 'coming_soon',
  },
];

function downloadCsv(content: string, filename: string) {
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Normalize a header string for synonym lookup */
function normalizeHeader(header: string): string {
  return header
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // remove accents
    .replace(/[^a-z0-9]/g, '_')                       // non-alphanumeric → _
    .replace(/_+/g, '_')                               // collapse multiple _
    .replace(/^_|_$/g, '');                            // trim leading/trailing _
}

/** Detect entity type from CSV headers */
function detectEntityType(headers: string[]): DetectionResult {
  const normalizedHeaders = headers.map(normalizeHeader);
  const scores: Record<EntityType, number> = { produtos: 0, clientes: 0, pedidos: 0, itens_pedido: 0 };

  // Score each entity by keyword matches
  normalizedHeaders.forEach((nh) => {
    (Object.keys(ENTITY_DETECTION_KEYWORDS) as EntityType[]).forEach((entity) => {
      if (ENTITY_DETECTION_KEYWORDS[entity].includes(nh)) {
        scores[entity] += 2; // exact keyword match
      } else {
        // partial match
        const partialMatch = ENTITY_DETECTION_KEYWORDS[entity].some(
          (kw) => nh.includes(kw) || kw.includes(nh)
        );
        if (partialMatch) scores[entity] += 1;
      }
    });

    // Also score via synonym map
    const syn = SYNONYM_MAP[nh];
    if (syn) {
      syn.entities.forEach((e) => { scores[e] += 3; });
    }
  });

  // Determine best entity
  const sorted = (Object.entries(scores) as [EntityType, number][]).sort((a, b) => b[1] - a[1]);
  const detectedEntity = sorted[0][0];
  const maxScore = sorted[0][1];
  const totalPossible = normalizedHeaders.length * 3;
  const confidence = totalPossible > 0 ? Math.min(Math.round((maxScore / totalPossible) * 100), 100) : 0;

  // Build auto-mapping for detected entity
  const dbFields = ENTITY_FIELDS[detectedEntity];
  const autoMap: Record<string, string> = {};
  const usedDbFields = new Set<string>();

  headers.forEach((h) => {
    const nh = normalizeHeader(h);

    // 1. Exact match with DB field
    if (dbFields.includes(nh) && !usedDbFields.has(nh)) {
      autoMap[h] = nh;
      usedDbFields.add(nh);
      return;
    }

    // 2. Synonym dictionary match
    const syn = SYNONYM_MAP[nh];
    if (syn && dbFields.includes(syn.field) && !usedDbFields.has(syn.field)) {
      autoMap[h] = syn.field;
      usedDbFields.add(syn.field);
      return;
    }

    // 3. Fuzzy: check if normalized header contains or is contained by a DB field
    for (const f of dbFields) {
      if (!usedDbFields.has(f) && (nh.includes(f) || f.includes(nh)) && nh.length > 2) {
        autoMap[h] = f;
        usedDbFields.add(f);
        return;
      }
    }
  });

  const unmappedHeaders = headers.filter((h) => !autoMap[h]);

  return {
    detectedEntity,
    confidence,
    scores,
    mappedFields: autoMap,
    totalHeaders: headers.length,
    mappedCount: Object.keys(autoMap).length,
    unmappedHeaders,
  };
}

export default function IntegrationsPage() {
  const { t, language } = useLanguage();
  const { empresa } = useEmpresa();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const smartFileInputRef = useRef<HTMLInputElement>(null);

  const [activeIntegration, setActiveIntegration] = useState<IntegrationId | null>(null);
  const [csvStep, setCsvStep] = useState<CsvStep>('entity');
  const [entityType, setEntityType] = useState<EntityType | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<Record<string, string>[]>([]);
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({});
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ success: number; errors: string[]; closet_synced: number } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [showInstructions, setShowInstructions] = useState(false);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [apiForm, setApiForm] = useState({ apiKey: '', storeUrl: '' });

  // ---- Helpers ----

  const handleDownloadTemplate = (entity: EntityType) => {
    downloadCsv(CSV_TEMPLATES[entity], `modelo_${entity}.csv`);
    toast.success(language === 'pt' ? `Modelo ${entity}.csv baixado!` : `Template ${entity}.csv downloaded!`);
  };

  const handleDownloadExample = (entity: EntityType) => {
    downloadCsv(CSV_EXAMPLES[entity], `exemplo_${entity}.csv`);
    toast.success(language === 'pt' ? `Exemplo ${entity}.csv baixado!` : `Example ${entity}.csv downloaded!`);
  };

  const validateCsvData = (rows: Record<string, string>[], mapping: Record<string, string>, entity: EntityType): ValidationError[] => {
    const errors: ValidationError[] = [];
    const required = REQUIRED_FIELDS[entity];
    const mappedDbFields = Object.values(mapping);
    const missingRequired = required.filter((f) => !mappedDbFields.includes(f));
    missingRequired.forEach((field) => {
      errors.push({ row: 0, field, message: language === 'pt' ? `Campo obrigatório "${field}" não está mapeado` : `Required field "${field}" is not mapped` });
    });
    const rev: Record<string, string> = {};
    Object.entries(mapping).forEach(([c, d]) => { rev[d] = c; });
    rows.forEach((row, idx) => {
      required.forEach((field) => {
        const csvCol = rev[field];
        if (csvCol && (!row[csvCol] || row[csvCol].trim() === '')) {
          errors.push({ row: idx + 1, field, message: language === 'pt' ? `Linha ${idx + 1}: campo "${field}" está vazio` : `Row ${idx + 1}: field "${field}" is empty` });
        }
      });
      // Price validation
      ['preco', 'valor_total', 'preco_unitario'].forEach((pf) => {
        if (rev[pf]) {
          const val = row[rev[pf]];
          if (val && isNaN(parseFloat(val.replace(',', '.')))) {
            errors.push({ row: idx + 1, field: pf, message: language === 'pt' ? `Linha ${idx + 1}: valor inválido "${val}" no campo ${pf}` : `Row ${idx + 1}: invalid value "${val}" in field ${pf}` });
          }
        }
      });
      // Integer validation
      ['estoque', 'quantidade'].forEach((intf) => {
        if (rev[intf]) {
          const val = row[rev[intf]];
          if (val && isNaN(parseInt(val))) {
            errors.push({ row: idx + 1, field: intf, message: language === 'pt' ? `Linha ${idx + 1}: valor inteiro inválido "${val}" no campo ${intf}` : `Row ${idx + 1}: invalid integer "${val}" in field ${intf}` });
          }
        }
      });
      // Date validation
      ['data_pedido', 'data_cadastro'].forEach((df) => {
        if (rev[df]) {
          const val = row[rev[df]];
          if (val && !/^\d{4}[-/]\d{2}[-/]\d{2}/.test(val) && !/^\d{2}[-/]\d{2}[-/]\d{4}/.test(val)) {
            errors.push({ row: idx + 1, field: df, message: language === 'pt' ? `Linha ${idx + 1}: data inválida "${val}" (use AAAA-MM-DD ou DD/MM/AAAA)` : `Row ${idx + 1}: invalid date "${val}" (use YYYY-MM-DD or DD/MM/YYYY)` });
          }
        }
      });
      // Status validation
      if (entity === 'pedidos' && rev['status']) {
        const val = row[rev['status']]?.toLowerCase();
        const valid = ['pendente', 'pago', 'enviado', 'entregue', 'cancelado'];
        if (val && !valid.includes(val)) {
          errors.push({ row: idx + 1, field: 'status', message: language === 'pt' ? `Linha ${idx + 1}: status inválido "${val}" (use: ${valid.join(', ')})` : `Row ${idx + 1}: invalid status "${val}" (use: ${valid.join(', ')})` });
        }
      }
    });
    return errors;
  };

  const parseCsvRaw = (text: string): { headers: string[]; rows: Record<string, string>[] } | null => {
    const lines = text.split('\n').filter((l) => l.trim());
    if (lines.length < 2) {
      toast.error(language === 'pt' ? 'CSV deve ter cabeçalho + linhas de dados' : 'CSV must have header + data rows');
      return null;
    }
    const sep = lines[0].includes(';') ? ';' : ',';
    const headers = lines[0].split(sep).map((h) => h.trim().replace(/^"|"$/g, ''));
    const rows: Record<string, string>[] = [];
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(sep).map((v) => v.trim().replace(/^"|"$/g, ''));
      const row: Record<string, string> = {};
      headers.forEach((h, idx) => { row[h] = values[idx] || ''; });
      rows.push(row);
    }
    return { headers, rows };
  };

  // Standard CSV parse (entity already selected)
  const parseCsv = (text: string) => {
    const result = parseCsvRaw(text);
    if (!result) return;
    setCsvHeaders(result.headers);
    setCsvRows(result.rows);
    if (entityType) {
      const dbFields = ENTITY_FIELDS[entityType];
      const autoMap: Record<string, string> = {};
      const usedFields = new Set<string>();
      result.headers.forEach((h) => {
        const nh = normalizeHeader(h);
        // Exact match
        if (dbFields.includes(nh) && !usedFields.has(nh)) { autoMap[h] = nh; usedFields.add(nh); return; }
        // Synonym match
        const syn = SYNONYM_MAP[nh];
        if (syn && dbFields.includes(syn.field) && !usedFields.has(syn.field)) { autoMap[h] = syn.field; usedFields.add(syn.field); return; }
        // Fuzzy
        for (const f of dbFields) {
          if (!usedFields.has(f) && (nh.includes(f) || f.includes(nh)) && nh.length > 2) { autoMap[h] = f; usedFields.add(f); return; }
        }
      });
      setFieldMapping(autoMap);
    }
    setValidationErrors([]);
    setCsvStep('mapping');
  };

  // Smart CSV parse (auto-detect entity)
  const parseSmartCsv = (text: string) => {
    const result = parseCsvRaw(text);
    if (!result) return;
    setCsvHeaders(result.headers);
    setCsvRows(result.rows);
    const detection = detectEntityType(result.headers);
    setDetectionResult(detection);
    setEntityType(detection.detectedEntity);
    setFieldMapping(detection.mappedFields);
    setValidationErrors([]);
    setCsvStep('detection');
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.csv') && !file.name.endsWith('.txt')) {
      toast.error(language === 'pt' ? 'Formato inválido. Use arquivos .csv ou .txt' : 'Invalid format. Use .csv or .txt files');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => parseCsv(ev.target?.result as string);
    reader.readAsText(file, 'UTF-8');
  };

  const handleSmartFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.csv') && !file.name.endsWith('.txt')) {
      toast.error(language === 'pt' ? 'Formato inválido. Use arquivos .csv ou .txt' : 'Invalid format. Use .csv or .txt files');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => parseSmartCsv(ev.target?.result as string);
    reader.readAsText(file, 'UTF-8');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.csv') && !file.name.endsWith('.txt')) {
      toast.error(language === 'pt' ? 'Formato inválido. Use arquivos .csv ou .txt' : 'Invalid format. Use .csv or .txt files');
      return;
    }
    const reader = new FileReader();
    const isSmart = activeIntegration === 'smart';
    reader.onload = (ev) => isSmart ? parseSmartCsv(ev.target?.result as string) : parseCsv(ev.target?.result as string);
    reader.readAsText(file, 'UTF-8');
  };

  const updateMapping = (csvCol: string, dbField: string) => {
    setFieldMapping((prev) => {
      const next = { ...prev };
      if (dbField === '') delete next[csvCol];
      else next[csvCol] = dbField;
      return next;
    });
    setValidationErrors([]);
  };

  const mappedCount = Object.keys(fieldMapping).length;

  const handleValidateAndImport = async () => {
    if (!empresa || !entityType) return;
    const errors = validateCsvData(csvRows, fieldMapping, entityType);
    setValidationErrors(errors);
    const criticalErrors = errors.filter((e) => e.row === 0);
    if (criticalErrors.length > 0) {
      toast.error(language === 'pt' ? 'Corrija os campos obrigatórios antes de importar' : 'Fix required fields before importing');
      return;
    }
    const rowErrors = errors.filter((e) => e.row > 0);
    if (rowErrors.length > 0) {
      const proceed = window.confirm(
        language === 'pt'
          ? `Encontramos ${rowErrors.length} aviso(s) nos dados. Deseja continuar com a importação?`
          : `Found ${rowErrors.length} warning(s) in data. Do you want to proceed with import?`
      );
      if (!proceed) return;
    }
    setImporting(true);
    try {
      const res = await client.apiCall.invoke({
        url: '/api/v1/import/process-csv',
        method: 'POST',
        data: { empresa_id: empresa.id, entity_type: entityType, field_mapping: fieldMapping, rows: csvRows },
      });
      setImportResult(res.data);
      setCsvStep('result');
      if (res.data.success > 0) toast.success(`${res.data.success} ${t('import.success')}`);
      if (res.data.closet_synced > 0) toast.success(`${res.data.closet_synced} ${t('import.syncDone')}`);
      if (res.data.errors?.length > 0) toast.error(`${res.data.errors.length} ${t('import.errors')}`);
    } catch (err) {
      console.error(err);
      toast.error(language === 'pt' ? 'Falha na importação' : 'Import failed');
    } finally { setImporting(false); }
  };

  const handleSyncCloset = async () => {
    if (!empresa) return;
    setSyncing(true);
    try {
      const res = await client.apiCall.invoke({ url: '/api/v1/import/sync-closet', method: 'POST', data: { empresa_id: empresa.id } });
      toast.success(`${res.data.new_entries} ${t('import.syncDone')}`);
    } catch (err) { console.error(err); toast.error('Sync failed'); }
    finally { setSyncing(false); }
  };

  const resetCsv = () => {
    setCsvStep('entity');
    setEntityType(null);
    setCsvHeaders([]);
    setCsvRows([]);
    setFieldMapping({});
    setImportResult(null);
    setValidationErrors([]);
    setShowInstructions(false);
    setDetectionResult(null);
  };

  const goBack = () => {
    if (activeIntegration === 'smart') {
      if (csvStep === 'detection') { resetCsv(); setActiveIntegration(null); return; }
      if (csvStep === 'mapping') { setCsvStep('detection'); return; }
      if (csvStep === 'result') { resetCsv(); setActiveIntegration(null); return; }
      setActiveIntegration(null); resetCsv(); return;
    }
    if (activeIntegration === 'csv') {
      if (csvStep === 'upload') { setCsvStep('entity'); return; }
      if (csvStep === 'mapping') { setCsvStep('upload'); return; }
      if (csvStep === 'result') { resetCsv(); return; }
    }
    setActiveIntegration(null);
    resetCsv();
  };

  const entityLabels: Record<EntityType, { pt: string; en: string; icon: string }> = {
    produtos: { pt: 'Catálogo de Produtos', en: 'Product Catalog', icon: '📦' },
    clientes: { pt: 'Base de Clientes', en: 'Customer Base', icon: '👥' },
    pedidos: { pt: 'Pedidos', en: 'Orders', icon: '🛒' },
    itens_pedido: { pt: 'Itens do Pedido', en: 'Order Items', icon: '📋' },
  };

  // No empresa guard
  if (!empresa) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <PlugZapIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('import.noEmpresa')}</h2>
          <Button onClick={() => navigate('/empresa')} className="bg-[#A3966A] hover:bg-[#895D2B] text-white mt-4">{t('empresa.title')}</Button>
        </div>
      </div>
    );
  }

  // ========== Integration Hub ==========
  if (!activeIntegration) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('integ.title')}</h1>
            <p className="text-muted-foreground">{t('integ.subtitle')}</p>
            <Badge className="mt-2 bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10">{empresa.nome_empresa}</Badge>
          </div>

          <Card className="mb-6 border-[#A3966A]/30 bg-[#A3966A]/5">
            <CardContent className="p-5 flex items-center gap-4">
              <ShirtIcon className="h-8 w-8 text-[#A3966A] flex-shrink-0" />
              <div className="flex-1">
                <h3 className="font-semibold text-foreground">{t('integ.autoCloset')}</h3>
                <p className="text-sm text-muted-foreground">{t('integ.autoClosetDesc')}</p>
              </div>
              <Button onClick={handleSyncCloset} disabled={syncing} variant="outline" className="border-[#A3966A] text-[#A3966A] flex-shrink-0">
                {syncing ? <Loader2Icon className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCwIcon className="h-4 w-4 mr-2" />}
                {syncing ? t('import.syncing') : t('integ.syncNow')}
              </Button>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {INTEGRATIONS.map((integ) => (
              <Card
                key={integ.id}
                className={`group cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${
                  integ.status === 'coming_soon' ? 'opacity-80' : ''
                } ${integ.id === 'smart' ? 'border-[#A3966A]/40 ring-1 ring-[#A3966A]/20' : ''}`}
                onClick={() => {
                  if (integ.status === 'available') setActiveIntegration(integ.id);
                  else toast.info(language === 'pt' ? `${integ.name} em breve!` : `${integ.name} coming soon!`);
                }}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="text-3xl">{integ.icon}</div>
                    {integ.id === 'smart' ? (
                      <Badge className="bg-[#A3966A] text-white hover:bg-[#A3966A] text-xs">{language === 'pt' ? '✨ Recomendado' : '✨ Recommended'}</Badge>
                    ) : integ.status === 'coming_soon' ? (
                      <Badge variant="secondary" className="text-xs">{language === 'pt' ? 'Em breve' : 'Coming soon'}</Badge>
                    ) : (
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100 text-xs">{language === 'pt' ? 'Disponível' : 'Available'}</Badge>
                    )}
                  </div>
                  <h3 className="text-lg font-bold text-foreground mb-1">{integ.name}</h3>
                  <p className="text-sm text-muted-foreground">{integ.description[language]}</p>
                  <div className="mt-4 flex items-center gap-1 text-sm font-medium" style={{ color: integ.color }}>
                    {integ.id === 'smart' ? (
                      <><BrainIcon className="h-4 w-4" />{language === 'pt' ? 'Importar Agora' : 'Import Now'}</>
                    ) : integ.status === 'available' ? (
                      <><LinkIcon className="h-4 w-4" />{language === 'pt' ? 'Conectar' : 'Connect'}</>
                    ) : (
                      <><ExternalLinkIcon className="h-4 w-4" />{language === 'pt' ? 'Saiba mais' : 'Learn more'}</>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="mt-8">
            <CardContent className="p-6">
              <h3 className="font-semibold text-foreground mb-3">{t('integ.multiTenant')}</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                {[
                  { icon: '📦', label: language === 'pt' ? 'Catálogo Próprio' : 'Own Catalog' },
                  { icon: '👥', label: language === 'pt' ? 'Clientes Próprios' : 'Own Customers' },
                  { icon: '🛒', label: language === 'pt' ? 'Pedidos Próprios' : 'Own Orders' },
                  { icon: '👗', label: language === 'pt' ? 'Closet dos Clientes' : 'Customer Closets' },
                ].map((item) => (
                  <div key={item.label} className="p-3 bg-muted/50 rounded-lg">
                    <div className="text-2xl mb-1">{item.icon}</div>
                    <span className="text-sm font-medium text-foreground">{item.label}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // ========== Smart Import Flow ==========
  if (activeIntegration === 'smart') {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center gap-2 mb-6">
            <Button variant="ghost" size="sm" onClick={goBack} className="text-muted-foreground hover:text-foreground">
              <ArrowLeftIcon className="h-4 w-4 mr-1" />
              {csvStep === 'entity' || !detectionResult ? t('integ.title') : t('common.cancel')}
            </Button>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm font-medium text-foreground flex items-center gap-1">
              <BrainIcon className="h-4 w-4" />
              {language === 'pt' ? 'Importação Inteligente' : 'Smart Import'}
            </span>
            {entityType && detectionResult && (
              <>
                <span className="text-muted-foreground">/</span>
                <Badge variant="secondary">{entityLabels[entityType][language]}</Badge>
              </>
            )}
          </div>

          {/* Smart Upload (no entity selection needed) */}
          {!detectionResult && csvStep !== 'mapping' && csvStep !== 'result' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-foreground mb-1 flex items-center gap-2">
                  <SparklesIcon className="h-6 w-6 text-[#A3966A]" />
                  {language === 'pt' ? 'Importação Inteligente' : 'Smart Import'}
                </h2>
                <p className="text-muted-foreground">
                  {language === 'pt'
                    ? 'Suba qualquer relatório CSV do seu ERP, CRM ou e-commerce. O sistema identifica automaticamente o tipo de dados e mapeia as colunas.'
                    : 'Upload any CSV report from your ERP, CRM or e-commerce. The system automatically identifies the data type and maps columns.'}
                </p>
              </div>

              {/* How it works */}
              <Card className="border-blue-200 bg-blue-50/50">
                <CardContent className="p-5">
                  <h4 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                    <InfoIcon className="h-4 w-4" />
                    {language === 'pt' ? 'Como funciona' : 'How it works'}
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      { step: '1', icon: '📤', title: language === 'pt' ? 'Envie seu arquivo' : 'Upload your file', desc: language === 'pt' ? 'Suba o CSV exportado do seu sistema, mesmo com nomes de colunas diferentes' : 'Upload the CSV exported from your system, even with different column names' },
                      { step: '2', icon: '🧠', title: language === 'pt' ? 'Detecção automática' : 'Auto-detection', desc: language === 'pt' ? 'A IA analisa os cabeçalhos e identifica se são produtos, clientes, pedidos ou itens' : 'AI analyzes headers and identifies if they are products, customers, orders or items' },
                      { step: '3', icon: '✅', title: language === 'pt' ? 'Confirme e importe' : 'Confirm and import', desc: language === 'pt' ? 'Revise o mapeamento sugerido, ajuste se necessário e importe com um clique' : 'Review the suggested mapping, adjust if needed and import with one click' },
                    ].map((s) => (
                      <div key={s.step} className="flex gap-3">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#A3966A] text-white flex items-center justify-center text-sm font-bold">{s.step}</div>
                        <div>
                          <p className="font-medium text-foreground text-sm">{s.icon} {s.title}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">{s.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Drop zone */}
              <Card>
                <CardContent className="p-6">
                  <div
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => smartFileInputRef.current?.click()}
                    className="border-2 border-dashed border-[#A3966A]/40 rounded-xl p-12 text-center cursor-pointer hover:border-[#A3966A] hover:bg-[#A3966A]/5 transition-all"
                  >
                    <BrainIcon className="h-14 w-14 text-[#A3966A]/60 mx-auto mb-4" />
                    <p className="text-lg font-medium text-foreground mb-1">
                      {language === 'pt' ? 'Arraste seu relatório CSV aqui' : 'Drag your CSV report here'}
                    </p>
                    <p className="text-sm text-muted-foreground mb-3">
                      {language === 'pt' ? 'ou clique para selecionar o arquivo' : 'or click to select file'}
                    </p>
                    <p className="text-xs text-[#A3966A] font-medium">
                      {language === 'pt'
                        ? '✨ Aceita relatórios de VTEX, Shopify, Bling, Tiny, Tray, Nuvemshop, Dito, Selbie e outros'
                        : '✨ Accepts reports from VTEX, Shopify, Bling, Tiny, Tray, Nuvemshop, Dito, Selbie and others'}
                    </p>
                    <input ref={smartFileInputRef} type="file" accept=".csv,.txt" className="hidden" onChange={handleSmartFileUpload} />
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Detection Result */}
          {csvStep === 'detection' && detectionResult && entityType && (
            <div className="space-y-6">
              {/* Detection summary */}
              <Card className="border-green-200 bg-green-50/50">
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-green-100 flex items-center justify-center text-3xl">
                      {entityLabels[detectionResult.detectedEntity].icon}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-bold text-green-900 mb-1">
                        {language === 'pt'
                          ? `Identificamos este arquivo como ${entityLabels[detectionResult.detectedEntity].pt}`
                          : `We identified this file as ${entityLabels[detectionResult.detectedEntity].en}`}
                      </h3>
                      <p className="text-sm text-green-700 mb-3">
                        {language === 'pt'
                          ? `Encontramos correspondência automática para ${detectionResult.mappedCount} de ${detectionResult.totalHeaders} colunas`
                          : `Found automatic match for ${detectionResult.mappedCount} of ${detectionResult.totalHeaders} columns`}
                      </p>

                      {/* Confidence & scores */}
                      <div className="flex flex-wrap gap-2 mb-3">
                        <Badge className="bg-green-600 text-white hover:bg-green-600">
                          {language === 'pt' ? `Confiança: ${detectionResult.confidence}%` : `Confidence: ${detectionResult.confidence}%`}
                        </Badge>
                        {detectionResult.unmappedHeaders.length > 0 && (
                          <Badge variant="outline" className="text-amber-700 border-amber-300">
                            {detectionResult.unmappedHeaders.length} {language === 'pt' ? 'colunas não mapeadas' : 'unmapped columns'}
                          </Badge>
                        )}
                      </div>

                      {/* Other entity scores */}
                      <div className="flex flex-wrap gap-2">
                        {(Object.entries(detectionResult.scores) as [EntityType, number][])
                          .sort((a, b) => b[1] - a[1])
                          .map(([entity, score]) => (
                            <span key={entity} className={`text-xs px-2 py-1 rounded-full ${entity === detectionResult.detectedEntity ? 'bg-green-200 text-green-800 font-semibold' : 'bg-gray-100 text-gray-600'}`}>
                              {entityLabels[entity].icon} {entityLabels[entity][language]} ({score}pts)
                            </span>
                          ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Change entity type if wrong */}
              <Card>
                <CardContent className="p-4">
                  <p className="text-sm text-muted-foreground mb-3">
                    {language === 'pt'
                      ? 'A detecção está incorreta? Selecione o tipo correto:'
                      : 'Detection incorrect? Select the correct type:'}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(['produtos', 'clientes', 'pedidos', 'itens_pedido'] as EntityType[]).map((entity) => (
                      <button
                        key={entity}
                        onClick={() => {
                          setEntityType(entity);
                          // Re-run mapping for new entity
                          const dbFields = ENTITY_FIELDS[entity];
                          const autoMap: Record<string, string> = {};
                          const usedFields = new Set<string>();
                          csvHeaders.forEach((h) => {
                            const nh = normalizeHeader(h);
                            if (dbFields.includes(nh) && !usedFields.has(nh)) { autoMap[h] = nh; usedFields.add(nh); return; }
                            const syn = SYNONYM_MAP[nh];
                            if (syn && dbFields.includes(syn.field) && !usedFields.has(syn.field)) { autoMap[h] = syn.field; usedFields.add(syn.field); return; }
                            for (const f of dbFields) {
                              if (!usedFields.has(f) && (nh.includes(f) || f.includes(nh)) && nh.length > 2) { autoMap[h] = f; usedFields.add(f); return; }
                            }
                          });
                          setFieldMapping(autoMap);
                        }}
                        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-all ${
                          entityType === entity ? 'bg-[#A3966A] text-white border-[#A3966A]' : 'border-border hover:border-[#A3966A]'
                        }`}
                      >
                        {entityLabels[entity].icon} {entityLabels[entity][language]}
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Mapped columns preview */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <WandIcon className="h-5 w-5 text-[#A3966A]" />
                    {language === 'pt' ? 'Mapeamento Automático' : 'Auto Mapping'}
                  </CardTitle>
                  <CardDescription>
                    {language === 'pt'
                      ? 'Confirme ou ajuste o mapeamento antes de importar'
                      : 'Confirm or adjust the mapping before importing'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {csvHeaders.map((header) => {
                      const mapped = fieldMapping[header];
                      const isRequired = mapped && REQUIRED_FIELDS[entityType].includes(mapped);
                      return (
                        <div key={header} className="flex items-center gap-3 py-1.5">
                          <div className="w-2/5">
                            <span className={`text-sm font-medium px-2.5 py-1 rounded inline-block ${mapped ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                              {header}
                            </span>
                          </div>
                          <ArrowRightIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <div className="w-2/5">
                            <select
                              value={mapped || ''}
                              onChange={(e) => updateMapping(header, e.target.value)}
                              className={`w-full border rounded-md px-2.5 py-1.5 text-sm bg-background ${isRequired ? 'border-green-400' : mapped ? 'border-blue-300' : 'border-border'}`}
                            >
                              <option value="">{language === 'pt' ? '— ignorar —' : '— ignore —'}</option>
                              {ENTITY_FIELDS[entityType].map((field) => (
                                <option key={field} value={field}>
                                  {field} {REQUIRED_FIELDS[entityType].includes(field) ? '⚠️' : ''}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="w-6">
                            {mapped ? (
                              <CheckCircleIcon className={`h-5 w-5 ${isRequired ? 'text-green-500' : 'text-blue-400'}`} />
                            ) : (
                              <AlertCircleIcon className="h-5 w-5 text-muted-foreground/30" />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Data preview */}
                  <div className="mt-6">
                    <h4 className="text-sm font-semibold text-foreground mb-2">
                      {language === 'pt' ? `Pré-visualização (${csvRows.length} linhas)` : `Preview (${csvRows.length} rows)`}
                    </h4>
                    <div className="overflow-x-auto max-h-48 border rounded-lg">
                      <table className="w-full text-xs">
                        <thead className="bg-muted sticky top-0">
                          <tr>
                            <th className="px-2 py-1.5 text-left font-medium">#</th>
                            {Object.values(fieldMapping).map((field) => (
                              <th key={field} className={`px-2 py-1.5 text-left font-medium ${REQUIRED_FIELDS[entityType].includes(field) ? 'text-[#A3966A]' : ''}`}>
                                {field}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {csvRows.slice(0, 4).map((row, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="px-2 py-1.5 text-muted-foreground">{idx + 1}</td>
                              {Object.entries(fieldMapping).map(([csvCol, dbField]) => (
                                <td key={dbField} className="px-2 py-1.5 max-w-[120px] truncate">{row[csvCol] || '-'}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="flex gap-3 mt-6">
                    <Button onClick={() => { setCsvStep('mapping'); }} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                      <ZapIcon className="h-4 w-4 mr-2" />
                      {language === 'pt' ? 'Confirmar e Continuar' : 'Confirm and Continue'}
                    </Button>
                    <Button variant="outline" onClick={goBack}>
                      {language === 'pt' ? 'Cancelar' : 'Cancel'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Mapping step (shared) */}
          {csvStep === 'mapping' && entityType && (
            <div className="space-y-6">
              {detectionResult && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
                  <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0" />
                  <span className="text-sm text-green-800">
                    {language === 'pt'
                      ? `Tipo detectado: ${entityLabels[entityType].pt} · ${mappedCount} campos mapeados · ${csvRows.length} linhas`
                      : `Detected type: ${entityLabels[entityType].en} · ${mappedCount} fields mapped · ${csvRows.length} rows`}
                  </span>
                </div>
              )}

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPinIcon className="h-5 w-5 text-[#A3966A]" />
                    {language === 'pt' ? 'Mapeamento Final' : 'Final Mapping'}
                  </CardTitle>
                  <CardDescription>
                    {mappedCount}/{csvHeaders.length} {language === 'pt' ? 'campos mapeados' : 'fields mapped'} · {csvRows.length} {t('import.rowsFound')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-sm text-amber-800 flex items-center gap-2">
                      <AlertTriangleIcon className="h-4 w-4 flex-shrink-0" />
                      {language === 'pt'
                        ? `Campos obrigatórios: ${REQUIRED_FIELDS[entityType].join(', ')}`
                        : `Required fields: ${REQUIRED_FIELDS[entityType].join(', ')}`}
                    </p>
                  </div>
                  <div className="space-y-3">
                    {csvHeaders.map((header) => {
                      const mappedField = fieldMapping[header];
                      const isRequired = mappedField && REQUIRED_FIELDS[entityType].includes(mappedField);
                      return (
                        <div key={header} className="flex items-center gap-4">
                          <div className="w-1/3">
                            <span className="text-sm font-medium bg-muted px-3 py-1.5 rounded inline-block">{header}</span>
                          </div>
                          <ArrowRightIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <div className="w-1/3">
                            <select
                              value={fieldMapping[header] || ''}
                              onChange={(e) => updateMapping(header, e.target.value)}
                              className={`w-full border rounded-md px-3 py-1.5 text-sm bg-background ${isRequired ? 'border-green-400' : 'border-border'}`}
                            >
                              <option value="">{t('import.ignore')}</option>
                              {ENTITY_FIELDS[entityType].map((field) => (
                                <option key={field} value={field}>
                                  {field} {REQUIRED_FIELDS[entityType].includes(field) ? '⚠️' : ''}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="w-8">
                            {fieldMapping[header] ? (
                              <CheckCircleIcon className={`h-5 w-5 ${isRequired ? 'text-green-500' : 'text-blue-400'}`} />
                            ) : (
                              <AlertCircleIcon className="h-5 w-5 text-muted-foreground/40" />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {validationErrors.length > 0 && (
                <Card className="border-red-200">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-red-700">
                      <XCircleIcon className="h-5 w-5" />
                      {language === 'pt' ? `${validationErrors.length} Problema(s)` : `${validationErrors.length} Issue(s)`}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {validationErrors.slice(0, 20).map((err, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          {err.row === 0 ? <XCircleIcon className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" /> : <AlertTriangleIcon className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />}
                          <span className={err.row === 0 ? 'text-red-700' : 'text-amber-700'}>{err.message}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader><CardTitle>{t('import.preview')}</CardTitle></CardHeader>
                <CardContent>
                  <div className="overflow-x-auto max-h-64 border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-muted sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium">#</th>
                          {Object.values(fieldMapping).map((field) => (
                            <th key={field} className={`px-3 py-2 text-left font-medium ${REQUIRED_FIELDS[entityType].includes(field) ? 'text-[#A3966A]' : ''}`}>
                              {field} {REQUIRED_FIELDS[entityType].includes(field) ? '*' : ''}
                            </th>
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
                    <Button onClick={handleValidateAndImport} disabled={importing || mappedCount === 0} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                      {importing ? <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" />{t('import.importing')}</> : t('import.startImport')}
                    </Button>
                    <Button variant="outline" onClick={goBack}>{t('common.cancel')}</Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Result step (shared) */}
          {csvStep === 'result' && importResult && (
            <Card>
              <CardContent className="p-8 text-center">
                <CheckCircleIcon className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-2xl font-bold mb-2">{importResult.success} {t('import.success')}</h3>
                {importResult.closet_synced > 0 && (
                  <div className="flex items-center justify-center gap-2 mb-3">
                    <ShirtIcon className="h-5 w-5 text-[#A3966A]" />
                    <span className="text-[#A3966A] font-medium">{importResult.closet_synced} {t('import.syncDone')}</span>
                  </div>
                )}
                {importResult.errors.length > 0 && (
                  <div className="mt-4 text-left max-h-40 overflow-y-auto bg-red-50 rounded-lg p-4">
                    <p className="font-medium text-red-700 mb-2">{importResult.errors.length} {t('import.errors')}:</p>
                    {importResult.errors.slice(0, 10).map((err, i) => (
                      <p key={i} className="text-sm text-red-600">{err}</p>
                    ))}
                  </div>
                )}
                <div className="flex gap-3 justify-center mt-6">
                  <Button onClick={() => { resetCsv(); }} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                    <RefreshCwIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Importar Mais' : 'Import More'}
                  </Button>
                  <Button variant="outline" onClick={() => { setActiveIntegration(null); resetCsv(); }}>{t('integ.title')}</Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    );
  }

  // ========== Standard CSV Flow ==========
  if (activeIntegration === 'csv') {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center gap-2 mb-6">
            <Button variant="ghost" size="sm" onClick={goBack} className="text-muted-foreground hover:text-foreground">
              <ArrowLeftIcon className="h-4 w-4 mr-1" />
              {csvStep === 'entity' ? t('integ.title') : t('common.cancel')}
            </Button>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm font-medium text-foreground">Upload CSV</span>
            {entityType && (
              <>
                <span className="text-muted-foreground">/</span>
                <Badge variant="secondary" className="capitalize">{t(`import.${entityType}`)}</Badge>
              </>
            )}
          </div>

          {csvStep === 'entity' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-foreground mb-1">{t('import.selectEntity')}</h2>
                <p className="text-muted-foreground">{t('integ.csvDesc')}</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {(['produtos', 'clientes', 'pedidos', 'itens_pedido'] as EntityType[]).map((entity) => (
                  <button
                    key={entity}
                    onClick={() => { setEntityType(entity); setCsvStep('upload'); }}
                    className="p-6 rounded-xl border-2 border-border hover:border-[#A3966A] hover:shadow-md transition-all text-center"
                  >
                    <div className="text-3xl mb-3">{entityLabels[entity].icon}</div>
                    <span className="font-semibold text-foreground">{entityLabels[entity][language]}</span>
                    <p className="text-xs text-muted-foreground mt-1">{ENTITY_FIELDS[entity].length} {language === 'pt' ? 'campos' : 'fields'}</p>
                    {entity === 'pedidos' && (
                      <Badge className="mt-2 bg-[#A3966A]/10 text-[#A3966A] hover:bg-[#A3966A]/10 text-xs">+ auto closet</Badge>
                    )}
                  </button>
                ))}
              </div>

              <Card className="border-[#A3966A]/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <DownloadIcon className="h-5 w-5 text-[#A3966A]" />
                    {language === 'pt' ? 'Baixar Modelos CSV' : 'Download CSV Templates'}
                  </CardTitle>
                  <CardDescription>
                    {language === 'pt' ? 'Baixe os modelos para preencher com seus dados' : 'Download templates to fill with your data'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {(['produtos', 'clientes', 'pedidos', 'itens_pedido'] as EntityType[]).map((entity) => (
                      <div key={entity} className="flex items-center gap-2 p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                        <FileSpreadsheetIcon className="h-5 w-5 text-[#A3966A] flex-shrink-0" />
                        <span className="text-sm font-medium flex-1">{entityLabels[entity][language]}</span>
                        <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); handleDownloadTemplate(entity); }} className="text-xs h-7 px-2">
                          <DownloadIcon className="h-3 w-3 mr-1" />{language === 'pt' ? 'Modelo' : 'Template'}
                        </Button>
                        <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); handleDownloadExample(entity); }} className="text-xs h-7 px-2 border-[#A3966A] text-[#A3966A]">
                          <FileTextIcon className="h-3 w-3 mr-1" />{language === 'pt' ? 'Exemplo' : 'Example'}
                        </Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-[#A3966A]/20">
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <ShirtIcon className="h-6 w-6 text-[#A3966A]" />
                    <div>
                      <h3 className="font-semibold text-foreground text-sm">{t('import.syncCloset')}</h3>
                      <p className="text-xs text-muted-foreground">{t('integ.autoClosetDesc')}</p>
                    </div>
                  </div>
                  <Button onClick={handleSyncCloset} disabled={syncing} size="sm" variant="outline" className="border-[#A3966A] text-[#A3966A]">
                    {syncing ? <Loader2Icon className="h-4 w-4 animate-spin" /> : <RefreshCwIcon className="h-4 w-4" />}
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}

          {csvStep === 'upload' && entityType && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <UploadIcon className="h-5 w-5 text-[#A3966A]" />
                    {t('import.uploadCsv')}
                  </CardTitle>
                  <CardDescription>
                    {entityType === 'produtos' && (language === 'pt' ? 'Envie produtos.csv com SKU, nome, categoria, preço...' : 'Upload produtos.csv with SKU, name, category, price...')}
                    {entityType === 'clientes' && (language === 'pt' ? 'Envie clientes.csv com nome, email, telefone, tamanhos...' : 'Upload clientes.csv with name, email, phone, sizes...')}
                    {entityType === 'pedidos' && (language === 'pt' ? 'Envie pedidos.csv com número, data, valor, status.' : 'Upload pedidos.csv with number, date, total, status.')}
                    {entityType === 'itens_pedido' && (language === 'pt' ? 'Envie itens_pedido.csv com pedido_id, sku, quantidade...' : 'Upload itens_pedido.csv with order_id, sku, quantity...')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-3 mb-6">
                    <Button variant="outline" onClick={() => handleDownloadTemplate(entityType)} className="border-[#A3966A] text-[#A3966A] hover:bg-[#A3966A]/10">
                      <DownloadIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Baixar CSV Modelo' : 'Download CSV Template'}
                    </Button>
                    <Button variant="outline" onClick={() => handleDownloadExample(entityType)} className="border-[#895D2B] text-[#895D2B] hover:bg-[#895D2B]/10">
                      <FileTextIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Baixar CSV Preenchido de Exemplo' : 'Download Filled Example CSV'}
                    </Button>
                    <Button variant="ghost" onClick={() => setShowInstructions(!showInstructions)} className="text-muted-foreground">
                      <InfoIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Instruções' : 'Instructions'}
                    </Button>
                  </div>
                  {showInstructions && (
                    <div className="mb-6 bg-blue-50 border border-blue-200 rounded-xl p-5">
                      <h4 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                        <InfoIcon className="h-4 w-4" />{language === 'pt' ? 'Instruções de Preenchimento' : 'Filling Instructions'}
                      </h4>
                      <div className="space-y-2">
                        {Object.entries(FIELD_INSTRUCTIONS[entityType]).map(([field, info]) => (
                          <div key={field} className="flex items-start gap-2 text-sm">
                            <span className={`font-mono px-1.5 py-0.5 rounded text-xs flex-shrink-0 ${info.required ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>{field}</span>
                            <span className="text-blue-800">{info[language]}</span>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 pt-3 border-t border-blue-200">
                        <p className="text-xs text-blue-700">
                          {language === 'pt' ? '💡 Dica: Baixe o CSV de exemplo para ver o formato correto.' : '💡 Tip: Download the example CSV to see the correct format.'}
                        </p>
                      </div>
                    </div>
                  )}
                  <div
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="border-2 border-dashed border-[#A3966A]/30 rounded-xl p-12 text-center cursor-pointer hover:border-[#A3966A] hover:bg-[#A3966A]/5 transition-all"
                  >
                    <UploadIcon className="h-12 w-12 text-[#A3966A]/50 mx-auto mb-4" />
                    <p className="text-lg font-medium text-foreground mb-1">{t('import.dragDrop')}</p>
                    <p className="text-sm text-muted-foreground">.csv, .txt</p>
                    {entityType === 'pedidos' && (
                      <p className="text-xs text-[#A3966A] mt-3 font-medium">⚡ {language === 'pt' ? 'Pedidos entregues sincronizam o closet automaticamente' : 'Delivered orders auto-sync to customer closet'}</p>
                    )}
                    <input ref={fileInputRef} type="file" accept=".csv,.txt" className="hidden" onChange={handleFileUpload} />
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {csvStep === 'mapping' && entityType && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><MapPinIcon className="h-5 w-5 text-[#A3966A]" />{t('import.mapping')}</CardTitle>
                  <CardDescription>{mappedCount}/{csvHeaders.length} {language === 'pt' ? 'campos mapeados' : 'fields mapped'} · {csvRows.length} {t('import.rowsFound')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-sm text-amber-800 flex items-center gap-2">
                      <AlertTriangleIcon className="h-4 w-4 flex-shrink-0" />
                      {language === 'pt' ? `Campos obrigatórios: ${REQUIRED_FIELDS[entityType].join(', ')}` : `Required fields: ${REQUIRED_FIELDS[entityType].join(', ')}`}
                    </p>
                  </div>
                  <div className="space-y-3">
                    {csvHeaders.map((header) => {
                      const mappedField = fieldMapping[header];
                      const isRequired = mappedField && REQUIRED_FIELDS[entityType].includes(mappedField);
                      return (
                        <div key={header} className="flex items-center gap-4">
                          <div className="w-1/3"><span className="text-sm font-medium bg-muted px-3 py-1.5 rounded inline-block">{header}</span></div>
                          <ArrowRightIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <div className="w-1/3">
                            <select value={fieldMapping[header] || ''} onChange={(e) => updateMapping(header, e.target.value)} className={`w-full border rounded-md px-3 py-1.5 text-sm bg-background ${isRequired ? 'border-green-400' : 'border-border'}`}>
                              <option value="">{t('import.ignore')}</option>
                              {ENTITY_FIELDS[entityType].map((field) => (
                                <option key={field} value={field}>{field} {REQUIRED_FIELDS[entityType].includes(field) ? '⚠️' : ''}</option>
                              ))}
                            </select>
                          </div>
                          <div className="w-8">
                            {fieldMapping[header] ? <CheckCircleIcon className={`h-5 w-5 ${isRequired ? 'text-green-500' : 'text-blue-400'}`} /> : <AlertCircleIcon className="h-5 w-5 text-muted-foreground/40" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
              {validationErrors.length > 0 && (
                <Card className="border-red-200">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-red-700"><XCircleIcon className="h-5 w-5" />{language === 'pt' ? `${validationErrors.length} Problema(s)` : `${validationErrors.length} Issue(s)`}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {validationErrors.slice(0, 20).map((err, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          {err.row === 0 ? <XCircleIcon className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" /> : <AlertTriangleIcon className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />}
                          <span className={err.row === 0 ? 'text-red-700' : 'text-amber-700'}>{err.message}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
              <Card>
                <CardHeader><CardTitle>{t('import.preview')}</CardTitle></CardHeader>
                <CardContent>
                  <div className="overflow-x-auto max-h-64 border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-muted sticky top-0">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium">#</th>
                          {Object.values(fieldMapping).map((field) => (
                            <th key={field} className={`px-3 py-2 text-left font-medium ${REQUIRED_FIELDS[entityType].includes(field) ? 'text-[#A3966A]' : ''}`}>{field} {REQUIRED_FIELDS[entityType].includes(field) ? '*' : ''}</th>
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
                    <Button onClick={handleValidateAndImport} disabled={importing || mappedCount === 0} className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                      {importing ? <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" />{t('import.importing')}</> : t('import.startImport')}
                    </Button>
                    <Button variant="outline" onClick={() => setCsvStep('upload')}>{t('common.cancel')}</Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {csvStep === 'result' && importResult && (
            <Card>
              <CardContent className="p-8 text-center">
                <CheckCircleIcon className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-2xl font-bold mb-2">{importResult.success} {t('import.success')}</h3>
                {importResult.closet_synced > 0 && (
                  <div className="flex items-center justify-center gap-2 mb-3">
                    <ShirtIcon className="h-5 w-5 text-[#A3966A]" />
                    <span className="text-[#A3966A] font-medium">{importResult.closet_synced} {t('import.syncDone')}</span>
                  </div>
                )}
                {importResult.errors.length > 0 && (
                  <div className="mt-4 text-left max-h-40 overflow-y-auto bg-red-50 rounded-lg p-4">
                    <p className="font-medium text-red-700 mb-2">{importResult.errors.length} {t('import.errors')}:</p>
                    {importResult.errors.slice(0, 10).map((err, i) => <p key={i} className="text-sm text-red-600">{err}</p>)}
                  </div>
                )}
                <div className="flex gap-3 justify-center mt-6">
                  <Button onClick={resetCsv} className="bg-[#A3966A] hover:bg-[#895D2B] text-white"><RefreshCwIcon className="h-4 w-4 mr-2" />{language === 'pt' ? 'Importar Mais' : 'Import More'}</Button>
                  <Button variant="outline" onClick={() => { setActiveIntegration(null); resetCsv(); }}>{t('integ.title')}</Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    );
  }

  // ========== Platform Integration Detail ==========
  const currentInteg = INTEGRATIONS.find((i) => i.id === activeIntegration);
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Button variant="ghost" size="sm" onClick={goBack} className="text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeftIcon className="h-4 w-4 mr-1" />{t('integ.title')}
        </Button>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <span className="text-3xl">{currentInteg?.icon}</span>
              <div>
                <CardTitle className="text-2xl">{currentInteg?.name}</CardTitle>
                <CardDescription>{currentInteg?.description[language]}</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm text-amber-800 font-medium">
                🚧 {language === 'pt'
                  ? `A integração com ${currentInteg?.name} está em desenvolvimento.`
                  : `${currentInteg?.name} integration is under development.`}
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-foreground mb-3">{language === 'pt' ? 'O que será sincronizado:' : 'What will be synced:'}</h3>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { icon: '📦', label: language === 'pt' ? 'Produtos e catálogo' : 'Products & catalog' },
                  { icon: '👥', label: language === 'pt' ? 'Clientes e perfis' : 'Customers & profiles' },
                  { icon: '🛒', label: language === 'pt' ? 'Pedidos e histórico' : 'Orders & history' },
                  { icon: '👗', label: language === 'pt' ? 'Closet automático' : 'Auto closet sync' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg">
                    <span>{item.icon}</span><span className="text-sm font-medium">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              <div><Label>{language === 'pt' ? 'URL da Loja' : 'Store URL'}</Label>
                <Input value={apiForm.storeUrl} onChange={(e) => setApiForm({ ...apiForm, storeUrl: e.target.value })} placeholder={`https://minhaloja.${currentInteg?.id === 'vtex' ? 'vtexcommercestable.com.br' : 'myshopify.com'}`} />
              </div>
              <div><Label>API Key</Label>
                <Input type="password" value={apiForm.apiKey} onChange={(e) => setApiForm({ ...apiForm, apiKey: e.target.value })} placeholder="sk_live_..." />
              </div>
              <Button disabled className="w-full bg-gray-300 text-gray-500 cursor-not-allowed">{language === 'pt' ? 'Em breve' : 'Coming Soon'}</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}