#!/bin/bash

set -e

echo "=========================================="
echo "🚀 智能旅行助手部署脚本"
echo "=========================================="

# 检查环境
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 检查.env文件
if [ ! -f .env ]; then
    echo "⚠️  .env文件不存在，从.env.example复制..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ 已创建.env文件，请编辑配置后继续"
        echo "   需要配置的项:"
        echo "   - AMAP_API_KEY (高德地图API Key)"
        echo "   - LLM_API_KEY (大模型API Key)"
        exit 1
    else
        echo "❌ .env.example文件也不存在"
        exit 1
    fi
fi

# 检查必要配置
if ! grep -q "AMAP_API_KEY=your_" .env && grep -q "AMAP_API_KEY=" .env; then
    echo "✅ 高德地图API Key已配置"
else
    echo "⚠️  请配置AMAP_API_KEY"
    exit 1
fi

if ! grep -q "LLM_API_KEY=your_" .env && grep -q "LLM_API_KEY=" .env; then
    echo "✅ LLM API Key已配置"
else
    echo "⚠️  请配置LLM_API_KEY"
    exit 1
fi

echo ""
echo "📦 开始构建镜像..."
docker-compose build

echo ""
echo "🚀 启动服务..."
docker-compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 5

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📍 访问地址:"
echo "   前端: http://localhost"
echo "   后端API: http://localhost:8000"
echo "   API文档: http://localhost:8000/docs"
echo ""
echo "📋 常用命令:"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo "=========================================="
