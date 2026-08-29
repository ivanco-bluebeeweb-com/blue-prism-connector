# Blue Prism Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `blue-prism-connector`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(estate/hub URL) + `ui.Divider` + navigation `ui.ListItem`(Processes/Sessions/Resources/Queues) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Process List (center, `center_overlay=True`) | `ui.Stats`(Running sessions/Failed today/Resources online) + `ui.DataTable`(process name; sortable) | `DataTable` — обзор доступных процессов estate. |
| Session List | `ui.Select`(param_name="status_filter") + `ui.DataTable`(process, resource, status Badge Running/Completed/Terminated/Stopped, start time; sortable) | Табличная история/поток сессий (запусков процессов). |
| Session Detail | Back-button + `ui.KeyValue`(process/resource/duration) + `ui.Alert`(variant="error", если error info) + `ui.Row`(Button "Stop", "Terminate") | `Alert` для явного показа ошибки сессии. |
| Start Session Dialog | `ui.Dialog`(title="Запустить процесс?", content=`ui.MultiSelect`(resource_ids), confirm_label="Запустить") | Явный выбор runtime resources требует подтверждения через Dialog. |
| Work Queue List | `ui.DataTable`(queue name, pending/locked/completed/exception counts) → клик → Queue Item List | Обзор очередей с ключевыми счётчиками. |
| Queue Item List | `ui.DataTable`(reference, status Badge Pending/Locked/Completed/Exception; sortable) + `ui.Button`("Добавить item") | Управление элементами очереди. |
| Resource List | `ui.DataTable`(name, status Badge available/busy/offline; sortable) | Обзор Runtime Resources estate. |
| Credential Vault Viewer | `ui.DataTable`(name, type — метаданные без значений) | Список credential-записей без утечки секретов. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Hub/Auth Server URL]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__bp_sidebar` рендерит estate URL + разделы,
   `auto_action` открывает Process List.
2. Process List: клик на процесс → Start Session Dialog (MultiSelect resources)
   → confirm вызывает `start_session` → `refresh_panels` на Session List.
3. Session List: клик на строку → Session Detail (тот же center handler,
   параметр `session_id`) → "Stop"/"Terminate" — прямой Call ("Terminate" как
   более резкое действие получает `ui.Dialog` подтверждение, "Stop" — прямой Call,
   т.к. graceful).
4. Work Queue List → клик на очередь → Queue Item List (параметр `queue_id`).
5. App Settings — единственная точка входа через кнопку в сайдбаре.

## 3. Экраны (конкретно, по файлам `panels.py`)

1. `bp_sidebar` (`slot="left"`) — навигация, App settings button.
2. `bp_center` (`slot="center"`, `center_overlay=True`) — параметризован `view`
   (processes/sessions/session_detail/queues/queue_items/resources/credentials).
3. `bp_settings` (`slot="center"`, `panels_settings.py`) — Accordion с
   Connections/Hub URL.
