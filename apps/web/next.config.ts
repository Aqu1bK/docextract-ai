import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Phase 9B adds the API proxy rewrites here:
  // browser calls /api/v1/* → FastAPI at NEXT_PUBLIC_API_URL (avoids CORS in local dev).
};

export default nextConfig;
