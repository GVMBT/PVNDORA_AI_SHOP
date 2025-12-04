# PowerShell скрипт для получения runtime логов последних деплойментов всех проектов
# Использование: .\scripts\get_latest_deployment_logs.ps1 [-Follow]

param(
    [switch]$Follow
)

Write-Host "🔍 Получаю список проектов..." -ForegroundColor Cyan

# Получаем список проектов в JSON формате
$projectsJson = vercel project ls --json 2>$null

if (-not $projectsJson) {
    Write-Host "❌ Не удалось получить список проектов. Убедитесь, что вы авторизованы: vercel login" -ForegroundColor Red
    exit 1
}

# Парсим JSON
$projects = $projectsJson | ConvertFrom-Json

foreach ($project in $projects) {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "📦 Проект: $($project.name) ($($project.id))" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    # Получаем последний деплоймент
    $deploymentsJson = vercel list $project.name --json 2>$null
    
    if (-not $deploymentsJson) {
        Write-Host "⚠️  Нет деплойментов для проекта $($project.name)" -ForegroundColor Yellow
        continue
    }
    
    $deployments = $deploymentsJson | ConvertFrom-Json
    
    if ($deployments.Count -eq 0) {
        Write-Host "⚠️  Нет деплойментов для проекта $($project.name)" -ForegroundColor Yellow
        continue
    }
    
    $latestDeployment = $deployments[0]
    $deploymentId = $latestDeployment.uid
    $deploymentUrl = $latestDeployment.url
    
    Write-Host "🚀 Последний деплоймент: $deploymentId" -ForegroundColor Green
    Write-Host "🌐 URL: $deploymentUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📋 Runtime логи:" -ForegroundColor Magenta
    Write-Host "──────────────────────────────────────────" -ForegroundColor Gray
    
    if ($Follow) {
        # Следим за логами в реальном времени (до 5 минут)
        vercel logs $deploymentId --follow
    } else {
        # Получаем последние логи
        vercel logs $deploymentId
    }
    
    Write-Host ""
}

Write-Host ""
Write-Host "✅ Готово!" -ForegroundColor Green

