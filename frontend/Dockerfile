FROM node:20-alpine AS build

WORKDIR /app

# 复制package文件
COPY package.json pnpm-lock.yaml* package-lock.json* yarn.lock* ./

# 安装依赖
RUN if [ -f pnpm-lock.yaml ]; then npm i -g pnpm && pnpm i; \
    elif [ -f yarn.lock ]; then yarn; else npm i; fi

# 复制源代码
COPY . .

# 构建应用
RUN if [ -f pnpm-lock.yaml ]; then pnpm build; \
    elif [ -f yarn.lock ]; then yarn build; else npm run build; fi

# 生产阶段
FROM nginx:1.27-alpine

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]
