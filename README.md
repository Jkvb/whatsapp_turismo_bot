# whatsapp_turismo_bot

Módulo Odoo 18 Community para onboarding de prestadores turísticos con **doble entrada (WhatsApp + Web)**, aprobación interna y autogestión de perfil/publicaciones en portal.

## Propósito

`whatsapp_turismo_bot` extiende el ecosistema existente (`tourism_provider_portal`) con una arquitectura modular:

- Entrada principal por **WhatsApp** (Meta Cloud API).
- Entrada alternativa por **formulario web**.
- Núcleo de negocio compartido en servicio de onboarding (`tourism.onboarding.service`).
- Flujo de aprobación/rechazo para usuarios internos.
- Habilitación de acceso portal únicamente para prestadores aprobados.

## Supuestos sobre `tourism_provider_portal`

Este módulo reutiliza y/o extiende:

- modelo `tourism.provider`
- modelo `tourism.provider.category`
- vistas base: `view_tourism_provider_list`, `view_tourism_provider_form`, `view_tourism_provider_search`
- menú raíz: `tourism_provider_portal.menu_tourism_root`

> Si en tu implementación esos IDs cambian, ajusta los `ref` XML.

## Flujo WhatsApp (principal)

1. Meta envía eventos a `GET/POST /whatsapp/webhook`.
2. Se verifica token en GET (`hub.verify_token`).
3. En POST se procesa payload, se identifica remitente y se crea/recupera `whatsapp.bot.session`.
4. La máquina de estados guía el onboarding.
5. Los datos se consolidan en `tourism.provider` vía `tourism.onboarding.service`.
6. El prestador queda en `approval_state = pending`.

Estados conversacionales implementados:

- `start`
- `asking_business_name`
- `asking_responsible_name`
- `asking_category`
- `asking_phone`
- `asking_email`
- `asking_location`
- `asking_description`
- `asking_profile_photo`
- `completed`

## Flujo Web

1. Prestador accede a `/tourism/register`.
2. Completa formulario responsivo y simple.
3. `/tourism/register/submit` crea/actualiza `tourism.provider` por servicio central.
4. Se fija `onboarding_source = web` y `approval_state = pending`.
5. Se muestra confirmación de recepción.

## Flujo de aprobación interna

Desde backend:

- Acción `action_approve_provider`
  - crea usuario portal si no existe
  - vincula `portal_user_id`
  - cambia `approval_state = approved`
- Acción `action_reject_provider`
  - cambia `approval_state = rejected`
  - guarda observaciones en `approval_notes`

Servicio responsable: `provider.approval.service`.

## Portal del prestador

Rutas:

- `/my/tourism/profile`
- `/my/tourism/posts`
- `/tourism/feed`
- `/tourism/provider/<id>`

Capacidades:

- editar perfil (solo propio y aprobado)
- actualizar imagen de perfil y portada
- crear posts en borrador o publicar
- visualizar feed público (publicado + proveedor aprobado)

## Seguridad

Grupos:

- `group_tourism_admin`
- `group_tourism_reviewer`
- `group_tourism_portal_user`

Reglas incluidas:

- portal solo edita su propio `tourism.provider`
- portal solo administra sus propios `tourism.post`
- público solo ve posts publicados de proveedores aprobados
- sesiones de bot para grupos internos

## Parametrización (`ir.config_parameter`)

- `whatsapp_turismo_bot.whatsapp_verify_token`
- `whatsapp_turismo_bot.whatsapp_access_token`
- `whatsapp_turismo_bot.whatsapp_phone_number_id`
- `whatsapp_turismo_bot.whatsapp_business_account_id`
- `whatsapp_turismo_bot.whatsapp_graph_api_version`
- `whatsapp_turismo_bot.tourism_portal_base_url`
- `whatsapp_turismo_bot.tourism_default_country_code`

## Servicios

- `whatsapp.service`
  - envío de mensajes
  - parseo de payloads
  - descarga de media
- `tourism.onboarding.service`
  - creación/actualización unificada de providers
  - normalización base de datos web/WhatsApp
- `provider.approval.service`
  - aprobar/rechazar
  - crear y vincular usuario portal
- `tourism.media.service`
  - persistencia de imágenes de WhatsApp en campos binarios

## Instalación

1. Copia el addon en tu ruta de addons.
2. Actualiza lista de apps.
3. Instala `whatsapp_turismo_bot`.
4. Ajusta parámetros en **Ajustes > Parámetros del sistema**.

## Pruebas recomendadas

- Verificar webhook de Meta con token correcto/incorrecto.
- Simular payload `text` y `image` de WhatsApp.
- Registrar prestador por web y confirmar `pending`.
- Aprobar y validar creación de usuario portal.
- Acceder con usuario portal y editar perfil propio.
- Crear post y revisar visualización en `/tourism/feed`.

## TODO técnicos planteados

- endurecer validaciones de email/teléfono por país
- agregar plantillas WhatsApp aprobadas por Meta
- agregar reintentos/backoff y bitácora de errores HTTP
- soporte SEO con slug para `/tourism/provider/<slug>`
