import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { client } from '../lib/api';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  ShirtIcon, SparklesIcon, StoreIcon, UserIcon,
  LogOutIcon, MenuIcon, XIcon, GlobeIcon, BuildingIcon, UploadIcon,
  PackageIcon, UsersIcon, BarChart3Icon, PaletteIcon, BookOpenIcon,
  SlidersHorizontalIcon, BrainIcon,
} from 'lucide-react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useEmpresa } from '@/contexts/EmpresaContext';

interface User {
  id: string;
  email: string;
  name?: string;
  role: string;
}

export default function Header() {
  const [user, setUser] = useState<User | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const { language, setLanguage, t } = useLanguage();
  const { empresa } = useEmpresa();

  useEffect(() => { checkAuth(); }, []);

  const checkAuth = async () => {
    try {
      const res = await client.auth.me();
      if (res?.data) setUser(res.data);
    } catch { setUser(null); }
  };

  const handleLogin = async () => { await client.auth.toLogin(); };
  const handleLogout = async () => { await client.auth.logout(); setUser(null); };
  const toggleLanguage = () => { setLanguage(language === 'en' ? 'pt' : 'en'); };

  const mainNavLinks = [
    { to: '/empresa-dashboard', label: t('nav.dashboard'), icon: BarChart3Icon },
    { to: '/catalogo', label: t('nav.catalogo'), icon: PackageIcon },
    { to: '/clientes', label: t('nav.clientes'), icon: UsersIcon },
    { to: '/integrations', label: t('nav.integrations'), icon: UploadIcon },
    { to: '/stylist', label: t('nav.stylist'), icon: SparklesIcon },
  ];

  const moreNavLinks = [
    { to: '/brand-settings', label: language === 'pt' ? 'Identidade Visual' : 'Brand Identity', icon: PaletteIcon },
    { to: '/curated-looks', label: language === 'pt' ? 'Biblioteca de Looks' : 'Look Library', icon: BookOpenIcon },
    { to: '/brand-rules', label: language === 'pt' ? 'Regras IA' : 'AI Rules', icon: SlidersHorizontalIcon },
    { to: '/ai-learning', label: language === 'pt' ? 'Painel IA' : 'AI Dashboard', icon: BrainIcon },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight" style={{ fontFamily: "'DM Serif Display', serif", color: '#000000' }}>
              mood<span className="text-[#A3966A]">·</span>lab
            </span>
            <span className="text-xs font-medium text-[#A3966A] tracking-widest uppercase" style={{ fontFamily: "'DM Sans', sans-serif" }}>
              .AI
            </span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden lg:flex items-center gap-0.5">
            {mainNavLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive(link.to)
                    ? 'bg-[#A3966A]/10 text-[#A3966A]'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <link.icon className="h-4 w-4" />
                {link.label}
              </Link>
            ))}
            {/* More dropdown for brand tools */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className={`flex items-center gap-1.5 text-sm font-medium ${
                  moreNavLinks.some((l) => isActive(l.to)) ? 'text-[#A3966A]' : 'text-muted-foreground hover:text-foreground'
                }`}>
                  <BrainIcon className="h-4 w-4" />
                  {language === 'pt' ? 'Motor IA' : 'AI Engine'}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuLabel className="text-xs text-muted-foreground">{language === 'pt' ? 'Ferramentas da Marca' : 'Brand Tools'}</DropdownMenuLabel>
                {moreNavLinks.map((link) => (
                  <DropdownMenuItem key={link.to} asChild className="cursor-pointer">
                    <Link to={link.to}><link.icon className="mr-2 h-4 w-4" />{link.label}</Link>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </nav>

          {/* Right Side */}
          <div className="flex items-center gap-2">
            {empresa && (
              <Link to="/empresa" className="hidden md:flex items-center gap-1.5 text-xs bg-[#A3966A]/10 text-[#A3966A] px-2.5 py-1 rounded-full hover:bg-[#A3966A]/20 transition-colors">
                <BuildingIcon className="h-3 w-3" />
                {empresa.nome_empresa}
              </Link>
            )}

            <Button variant="ghost" size="sm" onClick={toggleLanguage} className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
              <GlobeIcon className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase">{language === 'en' ? 'PT' : 'EN'}</span>
            </Button>

            {user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                    <Avatar className="h-9 w-9">
                      <AvatarFallback className="bg-[#A3966A]/20 text-[#A3966A] font-semibold">
                        <UserIcon className="h-4 w-4" />
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuLabel className="text-xs text-muted-foreground">Menu</DropdownMenuLabel>
                  <DropdownMenuItem asChild className="cursor-pointer">
                    <Link to="/empresa"><BuildingIcon className="mr-2 h-4 w-4" />{t('empresa.manage')}</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild className="cursor-pointer">
                    <Link to="/shop"><StoreIcon className="mr-2 h-4 w-4" />{t('nav.shop')}</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild className="cursor-pointer">
                    <Link to="/wardrobe"><ShirtIcon className="mr-2 h-4 w-4" />{t('nav.wardrobe')}</Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="cursor-pointer">
                    <LogOutIcon className="mr-2 h-4 w-4" />{t('auth.signout')}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Button onClick={handleLogin} className="bg-[#A3966A] hover:bg-[#895D2B] text-white font-medium">
                {t('auth.signin')}
              </Button>
            )}

            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              {mobileMenuOpen ? <XIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Nav */}
        {mobileMenuOpen && (
          <div className="lg:hidden pb-4 border-t border-border pt-3">
            <nav className="flex flex-col gap-1">
              {[...mainNavLinks, ...moreNavLinks].map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive(link.to)
                      ? 'bg-[#A3966A]/10 text-[#A3966A]'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`}
                >
                  <link.icon className="h-4 w-4" />
                  {link.label}
                </Link>
              ))}
              <Link to="/empresa" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted">
                <BuildingIcon className="h-4 w-4" />{t('nav.empresa')}
              </Link>
              <Link to="/shop" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted">
                <StoreIcon className="h-4 w-4" />{t('nav.shop')}
              </Link>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}