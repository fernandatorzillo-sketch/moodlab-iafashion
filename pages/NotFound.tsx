import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { HomeIcon } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4">
      <h1 className="text-6xl font-bold text-[#C9A96E] mb-4">404</h1>
      <p className="text-xl text-foreground mb-2">Page Not Found</p>
      <p className="text-muted-foreground mb-8">The page you're looking for doesn't exist.</p>
      <Link to="/">
        <Button className="bg-[#C9A96E] hover:bg-[#B8985D] text-white">
          <HomeIcon className="h-4 w-4 mr-2" />
          Back to Home
        </Button>
      </Link>
    </div>
  );
}