/** @type {import('next').NextConfig} */
const nextConfig = {
  // Netlify Next.js runtime handles SSR/ISR — no static export so dynamic [id] routes work
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};
module.exports = nextConfig;
