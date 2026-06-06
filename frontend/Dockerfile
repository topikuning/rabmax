# Frontend Dockerfile - Next.js 15 standalone build
FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Rebuild source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* HARUS tersedia saat build (di-bake ke bundle, bukan runtime).
# Railway menyediakan service variables sebagai build args otomatis untuk build
# Dockerfile — set `NEXT_PUBLIC_API_URL` di Variables service frontend.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Pastikan folder public selalu ada agar COPY di bawah tidak gagal.
RUN mkdir -p public && npm run build

# Production image
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
# HOSTNAME wajib 0.0.0.0. PORT default 3000 (Railway override saat runtime).
ENV HOSTNAME=0.0.0.0 PORT=3000
CMD ["node", "server.js"]
