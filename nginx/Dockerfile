FROM nginx:alpine

# 安装必要的工具
RUN apk add --no-cache curl

# 复制配置文件
COPY nginx.conf /etc/nginx/nginx.conf

# 复制静态文件
COPY static/ /usr/share/nginx/html/

# 创建必要的目录
RUN mkdir -p /var/log/nginx /etc/nginx/ssl

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# 暴露端口
EXPOSE 80 443

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]