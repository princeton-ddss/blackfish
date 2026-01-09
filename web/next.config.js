/** @type {import('next').NextConfig} */
const nextConfig = {
    // comment below for nextjs build
    output: 'export',
    distDir: process.env.DIST_DIR || 'build',
    assetPrefix: process.env.ASSET_PREFIX || '',
    basePath: process.env.BASE_PATH || '',
    images: {
        unoptimized: true,
    },
    env: {
        "basePath": process.env.BASE_PATH || '',
    }
}

module.exports = nextConfig
