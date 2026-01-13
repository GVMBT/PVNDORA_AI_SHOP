# Настройка SonarCloud

SonarCloud — это облачный сервис для анализа качества кода. Бесплатно для публичных репозиториев.

## Шаг 1: Регистрация на SonarCloud

1. Перейдите на https://sonarcloud.io
2. Войдите через GitHub
3. Авторизуйте доступ к вашему репозиторию

## Шаг 2: Создание проекта

1. В SonarCloud нажмите "Create Project"
2. Выберите "GitHub"
3. Выберите ваш репозиторий `pvndora`
4. Запишите **Organization Key** и **Project Key**

## Шаг 3: Обновление конфигурации

1. Откройте `sonar-project.properties`
2. Замените `your-org-name` на ваш Organization Key из SonarCloud
3. При необходимости обновите `sonar.projectKey`

## Шаг 4: Получение токена

1. В SonarCloud перейдите: **My Account → Security**
2. Создайте новый токен (Token type: `Project Analysis`)
3. Скопируйте токен

## Шаг 5: Добавление секрета в GitHub

1. Перейдите в ваш GitHub репозиторий
2. **Settings → Secrets and variables → Actions**
3. Добавьте новый секрет:
   - **Name:** `SONAR_TOKEN`
   - **Value:** токен из шага 4

## Шаг 6: Проверка интеграции

После настройки при каждом push в `main` или создании Pull Request:
- SonarCloud автоматически проанализирует код
- Результаты появятся в SonarCloud Dashboard
- Если включены Quality Gates, проверка может блокировать merge PR

## Локальная проверка (опционально)

Можно запустить анализ локально:

```bash
# Установите SonarScanner
npm install -g sonarqube-scanner

# Запустите анализ
sonar-scanner \
  -Dsonar.projectKey=pvndora \
  -Dsonar.organization=your-org-name \
  -Dsonar.sources=src,api,core \
  -Dsonar.host.url=https://sonarcloud.io \
  -Dsonar.login=YOUR_TOKEN
```

## Альтернатива: SonarLint (уже установлен)

SonarLint работает только локально в VS Code и показывает проблемы в реальном времени. Для командной работы и CI/CD используйте SonarCloud.
