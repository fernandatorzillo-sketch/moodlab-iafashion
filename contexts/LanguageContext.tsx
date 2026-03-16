import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Language = 'en' | 'pt';

interface Translations {
  [key: string]: { en: string; pt: string };
}

const translations: Translations = {
  // Header & Nav
  'nav.shop': { en: 'Shop', pt: 'Loja' },
  'nav.wardrobe': { en: 'My Wardrobe', pt: 'Meu Closet' },
  'nav.stylist': { en: 'AI Stylist', pt: 'Estilista IA' },
  'nav.dashboard': { en: 'Dashboard', pt: 'Painel' },
  'nav.empresa': { en: 'Company', pt: 'Empresa' },
  'nav.import': { en: 'Import', pt: 'Importar' },
  'nav.catalogo': { en: 'Catalog', pt: 'Catálogo' },
  'nav.clientes': { en: 'Customers', pt: 'Clientes' },
  'auth.signin': { en: 'Sign In', pt: 'Entrar' },
  'auth.signout': { en: 'Sign Out', pt: 'Sair' },

  // Landing Page
  'hero.badge': { en: 'AI-Powered Fashion', pt: 'Moda com Inteligência Artificial' },
  'hero.title1': { en: 'Your Intelligent', pt: 'Seu Assistente de' },
  'hero.title2': { en: 'Fashion Stylist', pt: 'Moda Inteligente' },
  'hero.description': {
    en: 'Build your virtual wardrobe, get AI-curated outfit recommendations for every occasion, and discover your unique style.',
    pt: 'Monte seu guarda-roupa virtual, receba recomendações de looks com IA para cada ocasião e descubra seu estilo único.',
  },
  'hero.explore': { en: 'Explore Collection', pt: 'Explorar Coleção' },
  'hero.try': { en: 'Try AI Stylist', pt: 'Experimentar Estilista IA' },

  // Features
  'features.title': { en: 'Fashion Meets Intelligence', pt: 'Moda Encontra Inteligência' },
  'features.subtitle': {
    en: 'Experience the future of personal styling with AI-powered recommendations tailored to your wardrobe.',
    pt: 'Experimente o futuro do estilo pessoal com recomendações de IA personalizadas para o seu guarda-roupa.',
  },
  'features.wardrobe.title': { en: 'Virtual Wardrobe', pt: 'Guarda-Roupa Virtual' },
  'features.wardrobe.desc': {
    en: 'Build your digital closet from every purchase. See all your pieces organized by category.',
    pt: 'Monte seu closet digital a partir de cada compra. Veja todas as peças organizadas por categoria.',
  },
  'features.ai.title': { en: 'AI Outfit Recommendations', pt: 'Recomendações de Looks com IA' },
  'features.ai.desc': {
    en: 'Our AI stylist creates complete looks from your wardrobe for any occasion.',
    pt: 'Nosso estilista IA cria looks completos do seu guarda-roupa para qualquer ocasião.',
  },
  'features.occasion.title': { en: 'Occasion-Based Styling', pt: 'Estilo por Ocasião' },
  'features.occasion.desc': {
    en: 'Beach, travel, dinner, or resort — get perfectly curated outfits for every event.',
    pt: 'Praia, viagem, jantar ou resort — receba looks perfeitamente curados para cada evento.',
  },
  'features.analytics.title': { en: 'Style Analytics', pt: 'Análise de Estilo' },
  'features.analytics.desc': {
    en: 'Discover your style preferences and trends with our intelligent dashboard.',
    pt: 'Descubra suas preferências de estilo e tendências com nosso painel inteligente.',
  },

  // CTA
  'cta.title': { en: 'Ready to Transform Your Style?', pt: 'Pronto para Transformar Seu Estilo?' },
  'cta.description': {
    en: 'Sign in to start building your virtual wardrobe and get personalized outfit recommendations.',
    pt: 'Entre para começar a montar seu guarda-roupa virtual e receber recomendações personalizadas de looks.',
  },
  'cta.button': { en: 'Get Started', pt: 'Começar Agora' },
  'footer.powered': { en: 'Powered by artificial intelligence.', pt: 'Impulsionado por inteligência artificial.' },

  // Shop Page
  'shop.title': { en: 'Shop Collection', pt: 'Coleção da Loja' },
  'shop.subtitle': {
    en: 'Browse our curated fashion collection and build your wardrobe.',
    pt: 'Navegue por nossa coleção de moda curada e monte seu guarda-roupa.',
  },
  'shop.all': { en: 'all', pt: 'todos' },
  'shop.tops': { en: 'tops', pt: 'blusas' },
  'shop.bottoms': { en: 'bottoms', pt: 'calças' },
  'shop.dresses': { en: 'dresses', pt: 'vestidos' },
  'shop.outerwear': { en: 'outerwear', pt: 'casacos' },
  'shop.shoes': { en: 'shoes', pt: 'sapatos' },
  'shop.accessories': { en: 'accessories', pt: 'acessórios' },
  'shop.addToWardrobe': { en: 'Add to Wardrobe', pt: 'Adicionar ao Closet' },
  'shop.owned': { en: 'Owned', pt: 'Adquirido' },
  'shop.adding': { en: 'Adding...', pt: 'Adicionando...' },
  'shop.added': { en: 'Added to your wardrobe!', pt: 'Adicionado ao seu closet!' },
  'shop.noProducts': { en: 'No products found', pt: 'Nenhum produto encontrado' },
  'shop.tryCategory': { en: 'Try selecting a different category.', pt: 'Tente selecionar uma categoria diferente.' },

  // Wardrobe Page
  'wardrobe.title': { en: 'My Wardrobe', pt: 'Meu Closet' },
  'wardrobe.pieces': { en: 'pieces in your virtual closet', pt: 'peças no seu closet virtual' },
  'wardrobe.piece': { en: 'piece in your virtual closet', pt: 'peça no seu closet virtual' },
  'wardrobe.getOutfit': { en: 'Get Outfit Ideas', pt: 'Obter Ideias de Looks' },
  'wardrobe.empty': { en: 'Your wardrobe is empty', pt: 'Seu closet está vazio' },
  'wardrobe.emptyDesc': { en: 'Start shopping to build your virtual closet!', pt: 'Comece a comprar para montar seu closet virtual!' },
  'wardrobe.browse': { en: 'Browse Collection', pt: 'Explorar Coleção' },
  'wardrobe.signinTitle': { en: 'Sign in to view your wardrobe', pt: 'Entre para ver seu closet' },
  'wardrobe.signinDesc': { en: 'Your virtual closet awaits. Sign in to see your purchased items.', pt: 'Seu closet virtual espera por você. Entre para ver seus itens comprados.' },

  // Stylist Page
  'stylist.badge': { en: 'AI-Powered', pt: 'Inteligência Artificial' },
  'stylist.title': { en: 'AI Stylist', pt: 'Estilista IA' },
  'stylist.subtitle': {
    en: 'Select an occasion and let our AI create the perfect outfit from your wardrobe.',
    pt: 'Selecione uma ocasião e deixe nossa IA criar o look perfeito do seu guarda-roupa.',
  },
  'stylist.using': { en: 'Using', pt: 'Usando' },
  'stylist.items': { en: 'items from your wardrobe', pt: 'itens do seu guarda-roupa' },
  'stylist.beach': { en: 'Beach', pt: 'Praia' },
  'stylist.travel': { en: 'Travel', pt: 'Viagem' },
  'stylist.dinner': { en: 'Dinner', pt: 'Jantar' },
  'stylist.resort': { en: 'Resort', pt: 'Resort' },
  'stylist.generating': { en: 'Creating your perfect look...', pt: 'Criando seu look perfeito...' },
  'stylist.analyzing': { en: 'Our AI is analyzing your wardrobe for the best', pt: 'Nossa IA está analisando seu guarda-roupa para o melhor look de' },
  'stylist.outfit': { en: 'outfit', pt: '' },
  'stylist.tips': { en: 'Styling Tips', pt: 'Dicas de Estilo' },
  'stylist.tryAnother': { en: 'Want to try another occasion?', pt: 'Quer experimentar outra ocasião?' },
  'stylist.emptyTitle': { en: 'Your wardrobe is empty', pt: 'Seu guarda-roupa está vazio' },
  'stylist.emptyDesc': { en: 'Add items from the shop to get AI outfit recommendations.', pt: 'Adicione itens da loja para receber recomendações de looks com IA.' },
  'stylist.browseShop': { en: 'Browse Shop', pt: 'Ir para a Loja' },
  'stylist.signinTitle': { en: 'Sign in to use AI Stylist', pt: 'Entre para usar o Estilista IA' },
  'stylist.signinDesc': { en: 'Get personalized outfit recommendations from your wardrobe.', pt: 'Receba recomendações personalizadas de looks do seu guarda-roupa.' },

  // Dashboard Page
  'dashboard.title': { en: 'Style Dashboard', pt: 'Painel de Estilo' },
  'dashboard.subtitle': { en: 'Customer style preferences and wardrobe analytics', pt: 'Preferências de estilo e análises do guarda-roupa' },
  'dashboard.totalProducts': { en: 'Total Products', pt: 'Total de Produtos' },
  'dashboard.totalPurchases': { en: 'Total Purchases', pt: 'Total de Compras' },
  'dashboard.aiRecs': { en: 'AI Recommendations', pt: 'Recomendações IA' },
  'dashboard.activeCustomers': { en: 'Active Customers', pt: 'Clientes Ativos' },
  'dashboard.popularCategories': { en: 'Popular Categories', pt: 'Categorias Populares' },
  'dashboard.occasionPrefs': { en: 'Occasion Preferences', pt: 'Preferências de Ocasião' },
  'dashboard.colorPrefs': { en: 'Color Preferences', pt: 'Preferências de Cores' },
  'dashboard.trendingStyles': { en: 'Trending Styles', pt: 'Estilos em Alta' },
  'dashboard.recentRecs': { en: 'Recent AI Recommendations', pt: 'Recomendações IA Recentes' },
  'dashboard.noPurchaseData': { en: 'No purchase data yet', pt: 'Sem dados de compras ainda' },
  'dashboard.noOccasionData': { en: 'No occasion data yet', pt: 'Sem dados de ocasião ainda' },
  'dashboard.noColorData': { en: 'No color preference data yet', pt: 'Sem dados de preferência de cor ainda' },
  'dashboard.noStyleData': { en: 'No style data yet', pt: 'Sem dados de estilo ainda' },
  'dashboard.noRecsYet': {
    en: 'No recommendations generated yet. Try the AI Stylist to see data here.',
    pt: 'Nenhuma recomendação gerada ainda. Experimente o Estilista IA para ver dados aqui.',
  },
  'dashboard.signinTitle': { en: 'Sign in to view the dashboard', pt: 'Entre para ver o painel' },
  'dashboard.signinDesc': { en: 'Access style analytics and customer insights.', pt: 'Acesse análises de estilo e insights de clientes.' },
  'dashboard.outfitSuffix': { en: 'Outfit', pt: 'Look' },
  'dashboard.user': { en: 'User', pt: 'Usuário' },

  // Empresa Setup
  'empresa.title': { en: 'Company Setup', pt: 'Configuração da Empresa' },
  'empresa.subtitle': { en: 'Register your company to start managing your fashion business', pt: 'Cadastre sua empresa para começar a gerenciar seu negócio de moda' },
  'empresa.name': { en: 'Company Name', pt: 'Nome da Empresa' },
  'empresa.email': { en: 'Admin Email', pt: 'Email do Administrador' },
  'empresa.platform': { en: 'E-commerce Platform', pt: 'Plataforma E-commerce' },
  'empresa.erp': { en: 'ERP System', pt: 'Sistema ERP' },
  'empresa.crm': { en: 'CRM System', pt: 'Sistema CRM' },
  'empresa.save': { en: 'Save Company', pt: 'Salvar Empresa' },
  'empresa.saved': { en: 'Company saved successfully!', pt: 'Empresa salva com sucesso!' },
  'empresa.select': { en: 'Select Company', pt: 'Selecionar Empresa' },
  'empresa.noCompany': { en: 'No company registered yet', pt: 'Nenhuma empresa cadastrada ainda' },
  'empresa.createFirst': { en: 'Create your first company to get started', pt: 'Crie sua primeira empresa para começar' },
  'empresa.current': { en: 'Current Company', pt: 'Empresa Atual' },
  'empresa.manage': { en: 'Manage Company', pt: 'Gerenciar Empresa' },
  'empresa.signinTitle': { en: 'Sign in to manage companies', pt: 'Entre para gerenciar empresas' },
  'empresa.signinDesc': { en: 'Access your multi-store management panel.', pt: 'Acesse seu painel de gestão multiloja.' },

  // Import Page
  'import.title': { en: 'Data Import', pt: 'Importação de Dados' },
  'import.subtitle': { en: 'Import your data via CSV or connect an external API', pt: 'Importe seus dados via CSV ou conecte uma API externa' },
  'import.csv': { en: 'CSV Import', pt: 'Importar CSV' },
  'import.api': { en: 'API Connection', pt: 'Conexão API' },
  'import.mapping': { en: 'Field Mapping', pt: 'Mapeamento de Campos' },
  'import.selectEntity': { en: 'Select data type', pt: 'Selecione o tipo de dado' },
  'import.clientes': { en: 'Customers', pt: 'Clientes' },
  'import.produtos': { en: 'Products', pt: 'Produtos' },
  'import.pedidos': { en: 'Orders', pt: 'Pedidos' },
  'import.itens_pedido': { en: 'Order Items', pt: 'Itens do Pedido' },
  'import.uploadCsv': { en: 'Upload CSV File', pt: 'Enviar Arquivo CSV' },
  'import.dragDrop': { en: 'Drag & drop or click to select', pt: 'Arraste e solte ou clique para selecionar' },
  'import.preview': { en: 'Data Preview', pt: 'Pré-visualização dos Dados' },
  'import.csvColumn': { en: 'CSV Column', pt: 'Coluna do CSV' },
  'import.dbField': { en: 'Database Field', pt: 'Campo do Banco' },
  'import.ignore': { en: '-- Ignore --', pt: '-- Ignorar --' },
  'import.startImport': { en: 'Start Import', pt: 'Iniciar Importação' },
  'import.importing': { en: 'Importing...', pt: 'Importando...' },
  'import.success': { en: 'records imported successfully', pt: 'registros importados com sucesso' },
  'import.errors': { en: 'errors occurred', pt: 'erros ocorridos' },
  'import.validation': { en: 'Data Validation', pt: 'Validação de Dados' },
  'import.valid': { en: 'Valid', pt: 'Válido' },
  'import.invalid': { en: 'Invalid', pt: 'Inválido' },
  'import.rowsFound': { en: 'rows found', pt: 'linhas encontradas' },
  'import.noEmpresa': { en: 'Please register a company first', pt: 'Por favor, cadastre uma empresa primeiro' },
  'import.syncCloset': { en: 'Sync Closet from Orders', pt: 'Sincronizar Closet dos Pedidos' },
  'import.syncing': { en: 'Syncing...', pt: 'Sincronizando...' },
  'import.syncDone': { en: 'new closet entries created', pt: 'novas entradas no closet criadas' },
  'import.apiUrl': { en: 'API Endpoint URL', pt: 'URL do Endpoint da API' },
  'import.apiKey': { en: 'API Key (optional)', pt: 'Chave da API (opcional)' },
  'import.testConnection': { en: 'Test Connection', pt: 'Testar Conexão' },

  // Catalogo Page
  'catalogo.title': { en: 'Product Catalog', pt: 'Catálogo de Produtos' },
  'catalogo.subtitle': { en: 'Synchronized product catalog for your company', pt: 'Catálogo de produtos sincronizado da sua empresa' },
  'catalogo.noProducts': { en: 'No products in catalog', pt: 'Nenhum produto no catálogo' },
  'catalogo.importFirst': { en: 'Import products to see them here', pt: 'Importe produtos para vê-los aqui' },
  'catalogo.active': { en: 'Active', pt: 'Ativo' },
  'catalogo.inactive': { en: 'Inactive', pt: 'Inativo' },
  'catalogo.stock': { en: 'Stock', pt: 'Estoque' },
  'catalogo.sku': { en: 'SKU', pt: 'SKU' },
  'catalogo.collection': { en: 'Collection', pt: 'Coleção' },
  'catalogo.total': { en: 'total products', pt: 'produtos no total' },

  // Clientes Page
  'clientes.title': { en: 'Customer Management', pt: 'Gestão de Clientes' },
  'clientes.subtitle': { en: 'View and manage your company customers', pt: 'Visualize e gerencie os clientes da sua empresa' },
  'clientes.noClients': { en: 'No customers found', pt: 'Nenhum cliente encontrado' },
  'clientes.importFirst': { en: 'Import customers to see them here', pt: 'Importe clientes para vê-los aqui' },
  'clientes.closetItems': { en: 'closet items', pt: 'itens no closet' },
  'clientes.orders': { en: 'orders', pt: 'pedidos' },
  'clientes.total': { en: 'total customers', pt: 'clientes no total' },
  'clientes.style': { en: 'Style', pt: 'Estilo' },
  'clientes.sizes': { en: 'Sizes', pt: 'Tamanhos' },

  // Empresa Dashboard
  'edash.title': { en: 'Company Dashboard', pt: 'Painel da Empresa' },
  'edash.subtitle': { en: 'Overview of your company data and operations', pt: 'Visão geral dos dados e operações da sua empresa' },
  'edash.totalClientes': { en: 'Total Customers', pt: 'Total de Clientes' },
  'edash.totalProdutos': { en: 'Total Products', pt: 'Total de Produtos' },
  'edash.totalPedidos': { en: 'Total Orders', pt: 'Total de Pedidos' },
  'edash.closetEntries': { en: 'Closet Entries', pt: 'Entradas no Closet' },
  'edash.recentOrders': { en: 'Recent Orders', pt: 'Pedidos Recentes' },
  'edash.topProducts': { en: 'Top Products', pt: 'Produtos Mais Vendidos' },
  'edash.noData': { en: 'No data yet. Import your data to see analytics.', pt: 'Sem dados ainda. Importe seus dados para ver análises.' },

  // Integrations Page
  'nav.integrations': { en: 'Integrations', pt: 'Integrações' },
  'integ.title': { en: 'Integrations', pt: 'Integrações' },
  'integ.subtitle': { en: 'Connect your platforms and import data to power your fashion business', pt: 'Conecte suas plataformas e importe dados para potencializar seu negócio de moda' },
  'integ.autoCloset': { en: 'Automatic Closet Sync', pt: 'Sincronização Automática do Closet' },
  'integ.autoClosetDesc': { en: 'When orders are imported, products are automatically added to the customer closet', pt: 'Quando pedidos são importados, os produtos são adicionados automaticamente ao closet do cliente' },
  'integ.syncNow': { en: 'Sync Now', pt: 'Sincronizar Agora' },
  'integ.csvDesc': { en: 'Select the type of data you want to import via CSV', pt: 'Selecione o tipo de dado que deseja importar via CSV' },
  'integ.multiTenant': { en: 'Each company has its own isolated data', pt: 'Cada empresa tem seus dados isolados' },

  // Common
  'common.loading': { en: 'Loading...', pt: 'Carregando...' },
  'common.save': { en: 'Save', pt: 'Salvar' },
  'common.cancel': { en: 'Cancel', pt: 'Cancelar' },
  'common.delete': { en: 'Delete', pt: 'Excluir' },
  'common.edit': { en: 'Edit', pt: 'Editar' },
  'common.search': { en: 'Search...', pt: 'Buscar...' },
  'common.noResults': { en: 'No results found', pt: 'Nenhum resultado encontrado' },
};

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType>({
  language: 'pt',
  setLanguage: () => {},
  t: (key: string) => key,
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem('moodlab-lang');
    return (saved === 'en' || saved === 'pt') ? saved : 'pt';
  });

  useEffect(() => {
    localStorage.setItem('moodlab-lang', language);
  }, [language]);

  const t = (key: string): string => {
    const entry = translations[key];
    if (!entry) return key;
    return entry[language] || entry['en'] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);