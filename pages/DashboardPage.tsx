import { useState, useEffect } from 'react';
import { client } from '@/lib/api';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboardIcon,
  UsersIcon,
  ShirtIcon,
  SparklesIcon,
  TrendingUpIcon,
  PaletteIcon,
  TagIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

interface StylePref {
  id: number;
  user_id: string;
  preferred_colors: string;
  preferred_styles: string;
  preferred_occasions: string;
}

interface OutfitRec {
  id: number;
  user_id: string;
  occasion: string;
  created_at: string;
}

interface Product {
  id: number;
  name: string;
  category: string;
  color: string;
  style_tags: string;
}

interface Purchase {
  id: number;
  user_id: string;
  product_id: number;
}

export default function DashboardPage() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalProducts: 0,
    totalPurchases: 0,
    totalRecommendations: 0,
    uniqueUsers: 0,
  });
  const [topCategories, setTopCategories] = useState<{ name: string; count: number }[]>([]);
  const [topColors, setTopColors] = useState<{ name: string; count: number }[]>([]);
  const [topOccasions, setTopOccasions] = useState<{ name: string; count: number }[]>([]);
  const [topStyles, setTopStyles] = useState<{ name: string; count: number }[]>([]);
  const [recentRecs, setRecentRecs] = useState<OutfitRec[]>([]);
  const { t } = useLanguage();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await client.auth.me();
      if (res?.data) {
        setUser(res.data);
        await fetchDashboardData();
      } else {
        setLoading(false);
      }
    } catch {
      setUser(null);
      setLoading(false);
    }
  };

  const fetchDashboardData = async () => {
    try {
      const [productsRes, purchasesRes, recsRes, prefsRes] = await Promise.all([
        client.entities.products.query({ query: {}, limit: 200 }),
        client.entities.purchases.queryAll({ query: {}, limit: 500 }),
        client.entities.outfit_recommendations.queryAll({ query: {}, limit: 200, sort: '-created_at' }),
        client.entities.style_preferences.queryAll({ query: {}, limit: 500 }),
      ]);

      const products: Product[] = productsRes.data?.items || [];
      const purchases: Purchase[] = purchasesRes.data?.items || [];
      const recommendations: OutfitRec[] = recsRes.data?.items || [];
      const preferences: StylePref[] = prefsRes.data?.items || [];

      const uniqueUserIds = new Set(purchases.map((p) => p.user_id));
      setStats({
        totalProducts: products.length,
        totalPurchases: purchases.length,
        totalRecommendations: recommendations.length,
        uniqueUsers: uniqueUserIds.size,
      });

      const categoryCount: Record<string, number> = {};
      purchases.forEach((purchase) => {
        const product = products.find((p) => p.id === purchase.product_id);
        if (product) {
          categoryCount[product.category] = (categoryCount[product.category] || 0) + 1;
        }
      });
      setTopCategories(
        Object.entries(categoryCount)
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 6)
      );

      const colorCount: Record<string, number> = {};
      preferences.forEach((pref) => {
        (pref.preferred_colors || '').split(',').filter(Boolean).forEach((c) => {
          const color = c.trim().toLowerCase();
          if (color) colorCount[color] = (colorCount[color] || 0) + 1;
        });
      });
      setTopColors(
        Object.entries(colorCount)
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 8)
      );

      const occasionCount: Record<string, number> = {};
      recommendations.forEach((rec) => {
        if (rec.occasion) {
          occasionCount[rec.occasion] = (occasionCount[rec.occasion] || 0) + 1;
        }
      });
      preferences.forEach((pref) => {
        (pref.preferred_occasions || '').split(',').filter(Boolean).forEach((o) => {
          const occ = o.trim().toLowerCase();
          if (occ) occasionCount[occ] = (occasionCount[occ] || 0) + 1;
        });
      });
      setTopOccasions(
        Object.entries(occasionCount)
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 4)
      );

      const styleCount: Record<string, number> = {};
      preferences.forEach((pref) => {
        (pref.preferred_styles || '').split(',').filter(Boolean).forEach((s) => {
          const style = s.trim().toLowerCase();
          if (style) styleCount[style] = (styleCount[style] || 0) + 1;
        });
      });
      setTopStyles(
        Object.entries(styleCount)
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 8)
      );

      setRecentRecs(recommendations.slice(0, 5));
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getBarWidth = (count: number, items: { count: number }[]) => {
    const max = Math.max(...items.map((i) => i.count), 1);
    return `${(count / max) * 100}%`;
  };

  if (!user && !loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <LayoutDashboardIcon className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold text-foreground mb-2">{t('dashboard.signinTitle')}</h2>
          <p className="text-muted-foreground mb-6">{t('dashboard.signinDesc')}</p>
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
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{t('dashboard.title')}</h1>
          <p className="text-muted-foreground">{t('dashboard.subtitle')}</p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-6">
                  <div className="h-4 bg-muted rounded w-1/2 mb-3" />
                  <div className="h-8 bg-muted rounded w-1/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <Card className="border-border hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">{t('dashboard.totalProducts')}</span>
                    <ShirtIcon className="h-5 w-5 text-[#A3966A]" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">{stats.totalProducts}</p>
                </CardContent>
              </Card>
              <Card className="border-border hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">{t('dashboard.totalPurchases')}</span>
                    <TrendingUpIcon className="h-5 w-5 text-[#895D2B]" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">{stats.totalPurchases}</p>
                </CardContent>
              </Card>
              <Card className="border-border hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">{t('dashboard.aiRecs')}</span>
                    <SparklesIcon className="h-5 w-5 text-[#90533C]" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">{stats.totalRecommendations}</p>
                </CardContent>
              </Card>
              <Card className="border-border hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-muted-foreground">{t('dashboard.activeCustomers')}</span>
                    <UsersIcon className="h-5 w-5 text-[#482D1E]" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">{stats.uniqueUsers}</p>
                </CardContent>
              </Card>
            </div>

            {/* Analytics Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Top Categories */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <TagIcon className="h-5 w-5 text-[#A3966A]" />
                    {t('dashboard.popularCategories')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {topCategories.length > 0 ? (
                    <div className="space-y-3">
                      {topCategories.map((cat) => (
                        <div key={cat.name} className="flex items-center gap-3">
                          <span className="text-sm font-medium capitalize w-24 flex-shrink-0">{cat.name}</span>
                          <div className="flex-1 bg-muted rounded-full h-6 overflow-hidden">
                            <div
                              className="h-full bg-[#A3966A]/70 rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                              style={{ width: getBarWidth(cat.count, topCategories) }}
                            >
                              <span className="text-xs font-medium text-white">{cat.count}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">{t('dashboard.noPurchaseData')}</p>
                  )}
                </CardContent>
              </Card>

              {/* Top Occasions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <SparklesIcon className="h-5 w-5 text-[#90533C]" />
                    {t('dashboard.occasionPrefs')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {topOccasions.length > 0 ? (
                    <div className="space-y-3">
                      {topOccasions.map((occ) => (
                        <div key={occ.name} className="flex items-center gap-3">
                          <span className="text-sm font-medium capitalize w-24 flex-shrink-0">{occ.name}</span>
                          <div className="flex-1 bg-muted rounded-full h-6 overflow-hidden">
                            <div
                              className="h-full bg-[#90533C]/70 rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                              style={{ width: getBarWidth(occ.count, topOccasions) }}
                            >
                              <span className="text-xs font-medium text-white">{occ.count}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">{t('dashboard.noOccasionData')}</p>
                  )}
                </CardContent>
              </Card>

              {/* Preferred Colors */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <PaletteIcon className="h-5 w-5 text-[#895D2B]" />
                    {t('dashboard.colorPrefs')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {topColors.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {topColors.map((color) => (
                        <Badge
                          key={color.name}
                          variant="outline"
                          className="capitalize px-3 py-1.5 text-sm"
                        >
                          {color.name}
                          <span className="ml-1.5 text-muted-foreground">({color.count})</span>
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">{t('dashboard.noColorData')}</p>
                  )}
                </CardContent>
              </Card>

              {/* Style Tags */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <TrendingUpIcon className="h-5 w-5 text-[#A3966A]" />
                    {t('dashboard.trendingStyles')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {topStyles.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {topStyles.map((style) => (
                        <Badge
                          key={style.name}
                          variant="outline"
                          className="capitalize px-3 py-1.5 text-sm"
                        >
                          {style.name}
                          <span className="ml-1.5 text-muted-foreground">({style.count})</span>
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">{t('dashboard.noStyleData')}</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Recent Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <SparklesIcon className="h-5 w-5 text-[#A3966A]" />
                  {t('dashboard.recentRecs')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {recentRecs.length > 0 ? (
                  <div className="space-y-3">
                    {recentRecs.map((rec) => (
                      <div
                        key={rec.id}
                        className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <SparklesIcon className="h-4 w-4 text-[#A3966A]" />
                          <div>
                            <span className="text-sm font-medium capitalize">{rec.occasion} {t('dashboard.outfitSuffix')}</span>
                            <p className="text-xs text-muted-foreground">
                              {t('dashboard.user')}: {rec.user_id?.substring(0, 8)}...
                            </p>
                          </div>
                        </div>
                        <Badge variant="secondary" className="capitalize">{rec.occasion}</Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    {t('dashboard.noRecsYet')}
                  </p>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}