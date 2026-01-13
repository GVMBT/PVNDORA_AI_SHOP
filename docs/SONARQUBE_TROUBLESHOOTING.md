# Решение проблемы "Project not found" в SonarCloud

## Проблема

При запуске `sonar-scanner` возникает ошибка:
```
[ERROR] Project not found. Please check the 'sonar.projectKey' and 'sonar.organization' properties
```

## Причины

1. **Проект не настроен для CLI анализа** - проекты, созданные через GitHub интеграцию, могут требовать специальной настройки
2. **Токен не имеет прав** - токен должен иметь права на анализ проекта
3. **Проект не существует** - проект нужно сначала создать в SonarCloud

## Решения

### Решение 1: Использовать GitHub Actions (рекомендуется)

Для проектов, подключенных через GitHub, лучше использовать автоматический анализ через GitHub Actions:

1. **Добавьте секрет в GitHub:**
   - Репозиторий → Settings → Secrets and variables → Actions
   - New repository secret: `SONAR_TOKEN` = ваш токен

2. **Создайте Pull Request:**
   - Анализ запустится автоматически
   - Результаты появятся в SonarCloud Dashboard

### Решение 2: Настроить проект для CLI анализа

1. **Откройте SonarCloud:**
   - https://sonarcloud.io/organizations/gvmbt/projects

2. **Выберите проект `PVNDORA_AI_SHOP`**

3. **Перейдите в Project Settings → Analysis Method**
   - Убедитесь, что выбрана опция "With SonarScanner" или "CI/CD"

4. **Проверьте токен:**
   - My Account → Security
   - Убедитесь, что токен имеет тип "Project Analysis" или "User Token"
   - Токен должен иметь права на организацию `gvmbt`

### Решение 3: Создать проект заново через CLI

Если проект еще не создан, можно создать его через анализ:

```bash
# Установите токен в текущей сессии PowerShell
$env:SONAR_TOKEN="your_token_here"

# Запустите анализ (проект создастся автоматически)
sonar-scanner
```

### Решение 4: Использовать Docker (обход проблем с PowerShell)

```bash
docker run --rm `
  -v "${PWD}:/usr/src" `
  -e SONAR_TOKEN="your_token" `
  -w /usr/src `
  sonarsource/sonar-scanner-cli
```

## Проверка конфигурации

Убедитесь, что в `sonar-project.properties`:
```properties
sonar.projectKey=GVMBT_PVNDORA_AI_SHOP
sonar.organization=gvmbt
sonar.host.url=https://sonarcloud.io
```

## Проверка токена

Токен должен быть установлен в текущей сессии:
```powershell
# Проверить токен
if ($env:SONAR_TOKEN) { 
    Write-Host "Token установлен (длина: $($env:SONAR_TOKEN.Length))" 
} else { 
    Write-Host "Token НЕ установлен" 
}

# Установить токен (если не установлен)
$env:SONAR_TOKEN="your_token_here"
```

## Рекомендация

Для вашего случая (проект уже подключен через GitHub):
- ✅ **Используйте GitHub Actions** - уже настроено в `.github/workflows/deploy.yml`
- ✅ **Создайте Pull Request** - анализ запустится автоматически
- ✅ **Проверьте результаты** в SonarCloud Dashboard

Локальный анализ через CLI может не работать для проектов, настроенных через GitHub интеграцию, если проект не был явно настроен для CLI анализа.
