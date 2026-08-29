# Blue Prism Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: RPA-оператор/
администратор Blue Prism Enterprise в регулируемой отрасли (банки, страхование).

## 1. Credential type
Self-hosted, двухкомпонентный URL (auth_server_url + api_base_url), вероятно + client
credentials далее в схеме — самый "enterprise" из RPA-коннекторов, требует явного
описания архитектуры (отдельный Auth Server от Hub/API).

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` с объяснением архитектуры Blue Prism (Authentication
   Server отдельно от Hub API) ДО формы — иначе пользователь не поймёт, зачем два URL.
2. **Форма** — auth_server_url + api_base_url, оба с явными лейблами и примерами.
3. **После успеха** — сводка ресурсов (runtime resources online/offline) и очередей
   работы (pending/failed) сразу — критично для регулируемой отрасли: аудируемость
   каждого запуска процесса.
4. **Audit trail emphasis** — идеально: т.к. Blue Prism ценят именно за строгий аудит —
   первый экран после подключения должен явно предлагать "посмотреть журнал аудита"
   как одну из первых опций, не прятать это глубоко в меню.
5. **Ошибка "auth server unreachable"** — self-hosted инфраструктура, конкретное
   сообщение отдельно для Auth Server vs Hub API недоступности (два разных хоста,
   два разных failure mode).
6. **Certificate/TLS strictness** — регулируемые отрасли часто используют внутренние
   CA — конкретное сообщение о проблеме сертификата, не общий network error.

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
