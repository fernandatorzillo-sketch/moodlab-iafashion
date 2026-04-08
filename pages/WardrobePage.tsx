import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Link } from 'react-router-dom';
import { ShirtIcon, ShoppingBagIcon, SparklesIcon } from 'lucide-react';
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

const CATEGORY_ORDER = ['tops', 'bottoms', 'dresses', 'outerwear', 'shoes', 'accessories'];

export default function WardrobePage() {
  const [wardrobeItems, setWardrobeItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const { t } = useLanguage();

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

  const groupedItems = CATEGORY_ORDER.reduce((acc, cat) => {
    const items = wardrobeItems.filter((item) => item.category === cat);
    if (items.length > 0) {
      acc[cat] = items;
    }
    return acc;
  }, {} as Record<string, Product[]>);

  const displayItems = selectedCategory
    ? { [selectedCategory]: groupedItems[selectedCategory] || [] }
    : groupedItems;

  if (!user && !loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <ShirtIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('wardrobe.signinTitle')}</h2>
          <p className="text-muted-foreground mb-6">{t('wardrobe.signinDesc')}</p>
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('wardrobe.title')}</h1>
            <p className="text-muted-foreground">
              {wardrobeItems.length} {wardrobeItems.length === 1 ? t('wardrobe.piece') : t('wardrobe.pieces')}
            </p>
          </div>
          <div className="flex gap-2">
            <Link to="/stylist">
              <Button className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                <SparklesIcon className="h-4 w-4 mr-2" />
                {t('wardrobe.getOutfit')}
              </Button>
            </Link>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-2">
          <Button
            variant={selectedCategory === null ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(null)}
            className={selectedCategory === null ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white' : ''}
          >
            {t('shop.all')} ({wardrobeItems.length})
          </Button>
          {CATEGORY_ORDER.map((cat) => {
            const count = (groupedItems[cat] || []).length;
            if (count === 0) return null;
            return (
              <Button
                key={cat}
                variant={selectedCategory === cat ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(cat)}
                className={`capitalize flex-shrink-0 ${
                  selectedCategory === cat ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white' : ''
                }`}
              >
                {cat} ({count})
              </Button>
            );
          })}
        </div>

        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i} className="overflow-hidden animate-pulse">
                <div className="aspect-square bg-muted" />
                <CardContent className="p-3">
                  <div className="h-3 bg-muted rounded mb-2 w-3/4" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : wardrobeItems.length === 0 ? (
          <div className="text-center py-16">
            <ShirtIcon className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-foreground mb-2">{t('wardrobe.empty')}</h3>
            <p className="text-muted-foreground mb-6">{t('wardrobe.emptyDesc')}</p>
            <Link to="/shop">
              <Button className="bg-[#A3966A] hover:bg-[#895D2B] text-white">
                <ShoppingBagIcon className="h-4 w-4 mr-2" />
                {t('wardrobe.browse')}
              </Button>
            </Link>
          </div>
        ) : (
          <div className="space-y-10">
            {Object.entries(displayItems).map(([category, items]) => (
              <div key={category}>
                <h2 className="text-xl font-bold text-foreground mb-4 capitalize flex items-center gap-2">
                  <ShirtIcon className="h-5 w-5 text-[#A3966A]" />
                  {category}
                  <Badge variant="secondary" className="ml-1">{items.length}</Badge>
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {items.map((item) => (
                    <Card
                      key={item.id}
                      className="overflow-hidden group hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5"
                    >
                      <div className="aspect-square overflow-hidden bg-muted">
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                      </div>
                      <CardContent className="p-3">
                        <h4 className="font-medium text-sm text-foreground line-clamp-1">{item.name}</h4>
                        <div className="flex items-center gap-1 mt-1">
                          <Badge variant="outline" className="text-xs capitalize">{item.color}</Badge>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}