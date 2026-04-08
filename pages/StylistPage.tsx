import { useState, useEffect, useRef } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  SparklesIcon,
  SunIcon,
  PlaneIcon,
  UtensilsIcon,
  PalmtreeIcon,
  ShirtIcon,
  Loader2Icon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

interface Product {
  id: number;
  name: string;
  description: string;
  price: number;
  image_url: string;
  category: string;
  color: string;
  style_tags: string;
}

interface OutfitItem {
  product_id: number;
  reason: string;
}

interface OutfitRecommendation {
  title: string;
  description: string;
  items: OutfitItem[];
  styling_tips: string;
}

export default function StylistPage() {
  const [user, setUser] = useState<any>(null);
  const [wardrobeItems, setWardrobeItems] = useState<Product[]>([]);
  const [selectedOccasion, setSelectedOccasion] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [recommendation, setRecommendation] = useState<OutfitRecommendation | null>(null);
  const [streamingText, setStreamingText] = useState('');
  const resultRef = useRef<HTMLDivElement>(null);
  const { t, language } = useLanguage();

  const OCCASIONS = [
    { id: 'beach', label: t('stylist.beach'), icon: SunIcon, color: '#895D2B', bg: '#F0DAAE' },
    { id: 'travel', label: t('stylist.travel'), icon: PlaneIcon, color: '#482D1E', bg: '#F0DAAE' },
    { id: 'dinner', label: t('stylist.dinner'), icon: UtensilsIcon, color: '#90533C', bg: '#F0DAAE' },
    { id: 'resort', label: t('stylist.resort'), icon: PalmtreeIcon, color: '#A3966A', bg: '#F0DAAE' },
  ];

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await client.auth.me();
      if (res?.data) {
        setUser(res.data);
        await fetchWardrobe();
      } else {
        setLoading(false);
      }
    } catch {
      setUser(null);
      setLoading(false);
    }
  };

  const fetchWardrobe = async () => {
    try {
      const purchasesRes = await client.entities.purchases.query({ query: {}, limit: 200 });
      const purchases = purchasesRes.data?.items || [];

      if (purchases.length === 0) {
        setWardrobeItems([]);
        setLoading(false);
        return;
      }

      const productsRes = await client.entities.products.query({ query: {}, limit: 100 });
      const allProducts: Product[] = productsRes.data?.items || [];
      const purchasedProductIds = new Set(purchases.map((p: any) => p.product_id));
      setWardrobeItems(allProducts.filter((p) => purchasedProductIds.has(p.id)));
    } catch (err) {
      console.error('Failed to fetch wardrobe:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateOutfit = async (occasion: string) => {
    if (wardrobeItems.length === 0) {
      toast.error(language === 'pt' ? 'Seu guarda-roupa está vazio. Adicione itens da loja primeiro!' : 'Your wardrobe is empty. Add items from the shop first!');
      return;
    }

    setSelectedOccasion(occasion);
    setGenerating(true);
    setRecommendation(null);
    setStreamingText('');

    const wardrobeDescription = wardrobeItems
      .map((item) => `ID:${item.id} - ${item.name} (${item.category}, ${item.color}, tags: ${item.style_tags})`)
      .join('\n');

    const langInstruction = language === 'pt'
      ? 'Respond in Brazilian Portuguese.'
      : 'Respond in English.';

    const prompt = `You are an expert fashion stylist. Based on the customer's wardrobe below, create a complete outfit recommendation for a "${occasion}" occasion. ${langInstruction}

WARDROBE:
${wardrobeDescription}

IMPORTANT: You must respond ONLY with valid JSON, no markdown, no code blocks. Use this exact format:
{
  "title": "A creative name for this outfit",
  "description": "A brief description of the overall look",
  "items": [
    {"product_id": <number>, "reason": "Why this piece works for the occasion"}
  ],
  "styling_tips": "Additional styling advice for this look"
}

Select 3-5 items that work well together for a ${occasion} occasion. Choose items from different categories (tops, bottoms, shoes, accessories, etc.) to create a complete look. Be specific about why each piece was chosen.`;

    try {
      let fullText = '';
      await client.ai.gentxt({
        messages: [
          { role: 'system', content: `You are a professional fashion stylist AI. Always respond with valid JSON only. ${langInstruction}` },
          { role: 'user', content: prompt },
        ],
        model: 'deepseek-v3.2',
        stream: true,
        onChunk: (chunk: any) => {
          fullText += chunk.content || '';
          setStreamingText(fullText);
        },
        onComplete: () => {
          try {
            let cleaned = fullText.trim();
            if (cleaned.startsWith('```json')) {
              cleaned = cleaned.slice(7);
            } else if (cleaned.startsWith('```')) {
              cleaned = cleaned.slice(3);
            }
            if (cleaned.endsWith('```')) {
              cleaned = cleaned.slice(0, -3);
            }
            cleaned = cleaned.trim();

            const parsed: OutfitRecommendation = JSON.parse(cleaned);
            setRecommendation(parsed);
            setStreamingText('');

            client.entities.outfit_recommendations.create({
              data: {
                occasion,
                recommendation: cleaned,
                created_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
              },
            }).catch(() => {});

            client.entities.style_preferences.create({
              data: {
                preferred_occasions: occasion,
                preferred_colors: wardrobeItems.map((i) => i.color).filter(Boolean).join(','),
                preferred_styles: wardrobeItems.flatMap((i) => (i.style_tags || '').split(',')).filter(Boolean).join(','),
                updated_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
              },
            }).catch(() => {});
          } catch {
            toast.error(language === 'pt' ? 'Falha ao processar resposta da IA. Tente novamente.' : 'Failed to parse AI response. Please try again.');
          }
          setGenerating(false);
        },
        onError: (error: any) => {
          toast.error(error?.message || (language === 'pt' ? 'Falha na geração com IA' : 'AI generation failed'));
          setGenerating(false);
        },
      });
    } catch (err) {
      console.error('AI generation error:', err);
      toast.error(language === 'pt' ? 'Falha ao gerar recomendação de look' : 'Failed to generate outfit recommendation');
      setGenerating(false);
    }
  };

  const getProductById = (id: number) => wardrobeItems.find((item) => item.id === id);

  if (!user && !loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <SparklesIcon className="h-16 w-16 text-[#A3966A] mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('stylist.signinTitle')}</h2>
          <p className="text-muted-foreground mb-6">{t('stylist.signinDesc')}</p>
          <Button
            onClick={() => client.auth.toLogin()}
            className="bg-[#A3966A] hover:bg-[#895D2B] text-white font-semibold"
          >
            {t('auth.signin')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-[#A3966A]/10 rounded-full px-4 py-1.5 mb-4">
            <SparklesIcon className="h-4 w-4 text-[#A3966A]" />
            <span className="text-sm font-medium text-[#A3966A]">{t('stylist.badge')}</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-3">{t('stylist.title')}</h1>
          <p className="text-muted-foreground max-w-lg mx-auto">
            {t('stylist.subtitle')}
            {wardrobeItems.length > 0 && (
              <span className="block mt-1 text-sm">
                {t('stylist.using')} {wardrobeItems.length} {t('stylist.items')}
              </span>
            )}
          </p>
        </div>

        {/* Occasion Selection */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {OCCASIONS.map((occasion) => (
            <button
              key={occasion.id}
              onClick={() => generateOutfit(occasion.id)}
              disabled={generating || wardrobeItems.length === 0}
              className={`group relative p-6 rounded-2xl border-2 transition-all duration-300 text-center ${
                selectedOccasion === occasion.id
                  ? 'border-[#A3966A] shadow-lg scale-[1.02]'
                  : 'border-border hover:border-[#A3966A]/50 hover:shadow-md'
              } ${generating || wardrobeItems.length === 0 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div
                className="w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-3 transition-transform group-hover:scale-110"
                style={{ backgroundColor: occasion.bg }}
              >
                <occasion.icon className="h-7 w-7" style={{ color: occasion.color }} />
              </div>
              <span className="font-semibold text-foreground">{occasion.label}</span>
            </button>
          ))}
        </div>

        {wardrobeItems.length === 0 && !loading && (
          <Card className="text-center py-10">
            <CardContent>
              <ShirtIcon className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
              <h3 className="text-lg font-semibold mb-2">{t('stylist.emptyTitle')}</h3>
              <p className="text-muted-foreground mb-4">{t('stylist.emptyDesc')}</p>
              <Button asChild className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                <a href="/shop">{t('stylist.browseShop')}</a>
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {generating && (
          <Card className="overflow-hidden">
            <CardContent className="p-8 text-center">
              <Loader2Icon className="h-10 w-10 text-[#A3966A] animate-spin mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">{t('stylist.generating')}</h3>
              <p className="text-sm text-muted-foreground mb-4">
                {t('stylist.analyzing')} {selectedOccasion} {t('stylist.outfit')}
              </p>
              {streamingText && (
                <div className="mt-4 p-4 bg-muted rounded-lg text-left text-sm text-muted-foreground max-h-40 overflow-y-auto">
                  <pre className="whitespace-pre-wrap font-mono text-xs">{streamingText.substring(0, 200)}...</pre>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Recommendation Result */}
        {recommendation && !generating && (
          <div ref={resultRef} className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Card className="overflow-hidden border-[#A3966A]/20">
              <CardHeader className="bg-gradient-to-r from-[#A3966A]/10 to-transparent">
                <div className="flex items-center gap-2 mb-1">
                  <SparklesIcon className="h-5 w-5 text-[#A3966A]" />
                  <Badge className="bg-[#A3966A] text-white capitalize hover:bg-[#A3966A]">
                    {selectedOccasion}
                  </Badge>
                </div>
                <CardTitle className="text-2xl">{recommendation.title}</CardTitle>
                <p className="text-muted-foreground">{recommendation.description}</p>
              </CardHeader>
              <CardContent className="p-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {recommendation.items.map((item, index) => {
                    const product = getProductById(item.product_id);
                    if (!product) return null;
                    return (
                      <Card key={index} className="overflow-hidden hover:shadow-md transition-shadow">
                        <div className="aspect-square overflow-hidden bg-muted">
                          <img
                            src={product.image_url}
                            alt={product.name}
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <CardContent className="p-3">
                          <h4 className="font-semibold text-sm mb-1">{product.name}</h4>
                          <Badge variant="outline" className="text-xs capitalize mb-2">{product.category}</Badge>
                          <p className="text-xs text-muted-foreground">{item.reason}</p>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                {recommendation.styling_tips && (
                  <div className="bg-[#A3966A]/5 rounded-xl p-4 border border-[#A3966A]/10">
                    <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                      <SparklesIcon className="h-4 w-4 text-[#A3966A]" />
                      {t('stylist.tips')}
                    </h4>
                    <p className="text-sm text-muted-foreground">{recommendation.styling_tips}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="text-center">
              <p className="text-sm text-muted-foreground mb-3">{t('stylist.tryAnother')}</p>
              <div className="flex justify-center gap-2 flex-wrap">
                {OCCASIONS.filter((o) => o.id !== selectedOccasion).map((occasion) => (
                  <Button
                    key={occasion.id}
                    variant="outline"
                    size="sm"
                    onClick={() => generateOutfit(occasion.id)}
                    className="gap-1"
                  >
                    <occasion.icon className="h-4 w-4" style={{ color: occasion.color }} />
                    {occasion.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}