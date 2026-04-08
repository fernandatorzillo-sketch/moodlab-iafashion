import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { ShoppingBagIcon, CheckIcon, FilterIcon } from 'lucide-react';
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

const CATEGORIES = ['all', 'tops', 'bottoms', 'dresses', 'outerwear', 'shoes', 'accessories'];

export default function ShopPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [purchasedIds, setPurchasedIds] = useState<Set<number>>(new Set());
  const [purchasing, setPurchasing] = useState<number | null>(null);
  const [user, setUser] = useState<any>(null);
  const { t } = useLanguage();

  useEffect(() => {
    fetchProducts();
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await client.auth.me();
      if (res?.data) {
        setUser(res.data);
        fetchPurchases();
      }
    } catch {
      setUser(null);
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await client.entities.products.query({ query: {}, sort: '-created_at', limit: 50 });
      setProducts(response.data?.items || []);
    } catch (err) {
      console.error('Failed to fetch products:', err);
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const fetchPurchases = async () => {
    try {
      const response = await client.entities.purchases.query({ query: {}, limit: 100 });
      const ids = new Set((response.data?.items || []).map((p: any) => p.product_id));
      setPurchasedIds(ids);
    } catch {
      // User might not be logged in
    }
  };

  const handlePurchase = async (productId: number) => {
    if (!user) {
      await client.auth.toLogin();
      return;
    }
    setPurchasing(productId);
    try {
      await client.entities.purchases.create({
        data: {
          product_id: productId,
          purchased_at: new Date().toISOString().replace('T', ' ').substring(0, 19),
        },
      });
      setPurchasedIds((prev) => new Set([...prev, productId]));
      toast.success(t('shop.added'));
    } catch (err) {
      console.error('Purchase failed:', err);
      toast.error('Failed to add to wardrobe');
    } finally {
      setPurchasing(null);
    }
  };

  const getCategoryLabel = (cat: string) => {
    const key = `shop.${cat}` as string;
    return t(key);
  };

  const filteredProducts = selectedCategory === 'all'
    ? products
    : products.filter((p) => p.category === selectedCategory);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('shop.title')}</h1>
          <p className="text-muted-foreground">{t('shop.subtitle')}</p>
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-2">
          <FilterIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          {CATEGORIES.map((cat) => (
            <Button
              key={cat}
              variant={selectedCategory === cat ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(cat)}
              className={`capitalize flex-shrink-0 ${
                selectedCategory === cat
                  ? 'bg-[#A3966A] hover:bg-[#895D2B] text-white'
                  : ''
              }`}
            >
              {getCategoryLabel(cat)}
            </Button>
          ))}
        </div>

        {/* Products Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} className="overflow-hidden animate-pulse">
                <div className="aspect-square bg-muted" />
                <CardContent className="p-4">
                  <div className="h-4 bg-muted rounded mb-2 w-3/4" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredProducts.map((product) => {
              const isPurchased = purchasedIds.has(product.id);
              return (
                <Card
                  key={product.id}
                  className="overflow-hidden group hover:shadow-xl transition-all duration-300 hover:-translate-y-1 border-border"
                >
                  <div className="aspect-square overflow-hidden bg-muted relative">
                    <img
                      src={product.image_url}
                      alt={product.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                    <Badge className="absolute top-3 left-3 capitalize bg-white/90 text-foreground hover:bg-white/90">
                      {product.category}
                    </Badge>
                  </div>
                  <CardContent className="p-4">
                    <h3 className="font-semibold text-foreground mb-1 line-clamp-1">{product.name}</h3>
                    <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{product.description}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-foreground">${product.price.toFixed(2)}</span>
                      <Button
                        size="sm"
                        disabled={isPurchased || purchasing === product.id}
                        onClick={() => handlePurchase(product.id)}
                        className={
                          isPurchased
                            ? 'bg-green-600 hover:bg-green-600 text-white cursor-default'
                            : 'bg-[#A3966A] hover:bg-[#895D2B] text-white'
                        }
                      >
                        {isPurchased ? (
                          <>
                            <CheckIcon className="h-4 w-4 mr-1" />
                            {t('shop.owned')}
                          </>
                        ) : purchasing === product.id ? (
                          t('shop.adding')
                        ) : (
                          <>
                            <ShoppingBagIcon className="h-4 w-4 mr-1" />
                            {t('shop.addToWardrobe')}
                          </>
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {!loading && filteredProducts.length === 0 && (
          <div className="text-center py-16">
            <ShoppingBagIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">{t('shop.noProducts')}</h3>
            <p className="text-muted-foreground">{t('shop.tryCategory')}</p>
          </div>
        )}
      </div>
    </div>
  );
}