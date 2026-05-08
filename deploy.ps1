# 智能旅行助手部署脚本 (PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🚀 智能旅行助手部署脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 检查Docker
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker未安装，请先安装Docker" -ForegroundColor Red
    exit 1
}

if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker Compose未安装，请先安装Docker Compose" -ForegroundColor Red
    exit 1
}

# 检查.env文件
if (!(Test-Path .env)) {
    Write-Host "⚠️  .env文件不存在，从.env.example复制..." -ForegroundColor Yellow
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "✅ 已创建.env文件，请编辑配置后继续" -ForegroundColor Green
        Write-Host "   需要配置的项:" -ForegroundColor Yellow
        Write-Host "   - AMAP_API_KEY (高德地图API Key)"
        Write-Host "   - LLM_API_KEY (大模型API Key)"
        exit 1
    } else {
        Write-Host "❌ .env.example文件也不存在" -ForegroundColor Red
        exit 1
    }
}

# 检查必要配置
$envContent = Get-Content .env -Raw
if ($envContent -match "AMAP_API_KEY=.+" -and $envContent -notmatch "AMAP_API_KEY=your_") {
    Write-Host "✅ 高德地图API Key已配置" -ForegroundColor Green
} else {
    Write-Host "⚠️  请配置AMAP_API_KEY" -ForegroundColor Yellow
    exit 1
}

if ($envContent -match "LLM_API_KEY=.+" -and $envContent -notmatch "LLM_API_KEY=your_") {
    Write-Host "✅ LLM API Key已配置" -ForegroundColor Green
} else {
    Write-Host "⚠️  请配置LLM_API_KEY" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📦 开始构建镜像..." -ForegroundColor Cyan
docker-compose build

Write-Host ""
Write-Host "🚀 启动服务..." -ForegroundColor Cyan
docker-compose up -d

Write-Host ""
Write-Host "⏳ 等待服务启动..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "✅ 部署完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📍 访问地址:" -ForegroundColor Cyan
Write-Host "   前端: http://localhost" -ForegroundColor White
Write-Host "   后端API: http://localhost:8000" -ForegroundColor White
Write-Host "   API文档: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "📋 常用命令:" -ForegroundColor Cyan
Write-Host "   查看日志: docker-compose logs -f" -ForegroundColor White
Write-Host "   停止服务: docker-compose down" -ForegroundColor White
Write-Host "   重启服务: docker-compose restart" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Green
