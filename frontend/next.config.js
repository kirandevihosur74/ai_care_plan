/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Removed rewrites - now using custom API routes for better timeout control
  // Custom API routes in app/api/orders/* handle proxying with longer timeouts
};

module.exports = nextConfig;
