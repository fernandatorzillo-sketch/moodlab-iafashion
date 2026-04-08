import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import Header from '@/components/Header';
import { SparklesIcon, ShirtIcon, WandIcon, BarChart3Icon, ArrowRightIcon } from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';

const HERO_IMAGE = 'https://mgx-backend-cdn.metadl.com/generate/images/1021619/2026-03-12/cbb45727-7787-4d25-a09e-73c6a8b07325.png';

export default function Index() {
  const { t } = useLanguage();

  const features = [
    {
      icon: ShirtIcon,
      title: t('features.wardrobe.title'),
      description: t('features.wardrobe.desc'),
    },
    {
      icon: SparklesIcon,
      title: t('features.ai.title'),
      description: t('features.ai.desc'),
    },
    {
      icon: WandIcon,
      title: t('features.occasion.title'),
      description: t('features.occasion.desc'),
    },
    {
      icon: BarChart3Icon,
      title: t('features.analytics.title'),
      description: t('features.analytics.desc'),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Header />

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img
            src={HERO_IMAGE}
            alt="Fashion hero"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#000000]/85 via-[#482D1E]/60 to-transparent" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 md:py-44">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 bg-[#A3966A]/20 backdrop-blur-sm border border-[#A3966A]/30 rounded-full px-4 py-1.5 mb-6">
              <SparklesIcon className="h-4 w-4 text-[#F0DAAE]" />
              <span className="text-sm font-medium text-[#F0DAAE]">{t('hero.badge')}</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold text-white leading-tight mb-6" style={{ fontFamily: "'DM Serif Display', serif" }}>
              {t('hero.title1')}
              <br />
              <span className="text-[#F0DAAE]">{t('hero.title2')}</span>
            </h1>
            <p className="text-lg text-white/80 mb-8 leading-relaxed">
              {t('hero.description')}
            </p>
            <div className="flex flex-wrap gap-4">
              <Link to="/shop">
                <Button size="lg" className="bg-[#A3966A] hover:bg-[#895D2B] text-white font-semibold px-8 h-12 text-base">
                  {t('hero.explore')}
                  <ArrowRightIcon className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link to="/stylist">
                <Button size="lg" variant="outline" className="border-[#F0DAAE]/40 text-[#F0DAAE] hover:bg-[#F0DAAE]/10 font-semibold px-8 h-12 text-base !bg-transparent">
                  {t('hero.try')}
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              {t('features.title')}
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {t('features.subtitle')}
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group bg-card rounded-2xl p-6 border border-border hover:border-[#A3966A]/30 hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
              >
                <div className="w-12 h-12 rounded-xl bg-[#A3966A]/10 flex items-center justify-center mb-4 group-hover:bg-[#A3966A]/20 transition-colors">
                  <feature.icon className="h-6 w-6 text-[#A3966A]" />
                </div>
                <h3 className="text-lg font-semibold text-foreground mb-2" style={{ fontFamily: "'DM Serif Display', serif" }}>
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-[#482D1E]">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-[#F0DAAE] mb-4">
            {t('cta.title')}
          </h2>
          <p className="text-lg text-[#F0DAAE]/70 mb-8">
            {t('cta.description')}
          </p>
          <Link to="/shop">
            <Button size="lg" className="bg-[#A3966A] hover:bg-[#895D2B] text-white font-semibold px-10 h-12 text-base">
              {t('cta.button')}
              <ArrowRightIcon className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 bg-background border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-sm text-muted-foreground">
            © 2026 Moodlab.AI. {t('footer.powered')}
          </p>
        </div>
      </footer>
    </div>
  );
}