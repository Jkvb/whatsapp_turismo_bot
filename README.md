# whatsapp_turismo_bot

Integración de **WhatsApp (Meta Cloud API)** con **Odoo 18** para el onboarding de prestadores turísticos, su aprobación interna en Odoo y la activación posterior de su acceso al portal web.

> **Regla principal del negocio:**  
> El registro inicial por web está prohibido.  
> El alta inicial del prestador se realiza **únicamente por WhatsApp**.

---

## Objetivo

Este proyecto extiende el ecosistema de turismo para que el flujo sea:

1. El prestador escribe por **WhatsApp**
2. El **chatbot** recopila su información
3. Odoo crea/actualiza el registro del prestador
4. Un administrador lo **aprueba** desde Odoo
5. Después de ser aprobado, el sistema le envía un enlace seguro para **activar su acceso web**
6. Ya dentro del portal, puede administrar su perfil y publicar contenido

---

## Relación con otros módulos

Este módulo está pensado para trabajar junto con:

- `tourism_provider_portal`  
  Portal web turístico, perfiles, publicaciones, feed y vistas públicas

Este módulo **no reemplaza** al portal.  
Su función es agregar la capa de:

- conversación por WhatsApp
- webhook con Meta Cloud API
- máquina de estados del chatbot
- aprobación y activación de acceso

---

## Flujo funcional

## 1. Registro inicial por WhatsApp

El usuario inicia conversación con el número oficial de WhatsApp del proyecto.

El bot sigue una máquina de estados para capturar los datos mínimos:

- nombre del negocio o prestador
- nombre del responsable
- categoría
- teléfono
- ubicación
- foto de perfil

Cuando el flujo termina:

- se crea o actualiza el registro en Odoo
- el prestador queda en estado **pending**
- se notifica que su solicitud está en revisión

---

## 2. Revisión y aprobación en Odoo

Desde el backend de Odoo, el comité o administrador revisa a los prestadores pendientes.

Opciones:

- **Aprobar**
- **Rechazar**

Cuando se aprueba:

- el prestador cambia a estado `approved`
- se crea un usuario portal si no existe
- se genera un **token de activación**
- se envía un mensaje de WhatsApp con un enlace seguro para activar su acceso web

---

## 3. Activación del acceso web

El usuario abre el enlace recibido por WhatsApp.

Si el token es válido:

- define su contraseña
- activa su acceso web
- queda vinculado con su usuario portal
- entra al portal para administrar su perfil

---

## 4. Actualización posterior por chatbot

Una vez registrado, el mismo chatbot puede ayudarle a actualizar:

- descripción
- teléfono
- ubicación
- foto de perfil
- portada
- otros campos permitidos

Dependiendo de la configuración del negocio, ciertos cambios pueden volver a dejar el perfil en revisión.

---

# Arquitectura

## Componentes principales

### 1. Webhook de WhatsApp
Controlador que recibe los eventos de Meta Cloud API.

Funciones:

- verificación del webhook
- recepción de mensajes entrantes
- procesamiento del payload
- respuesta automática
- descarga de media

### 2. Máquina de estados conversacional
Controla en qué paso va cada usuario durante el onboarding o actualización.

### 3. Persistencia en Odoo ORM
Toda la información recopilada por el bot se guarda mediante el ORM de Odoo.

### 4. Flujo de aprobación
Permite aprobar o rechazar prestadores desde el backend.

### 5. Activación de acceso web
Genera enlaces seguros de un solo uso para que el prestador cree su contraseña.

---

# Modelos principales

## `tourism.provider`
Modelo central del prestador turístico.

Campos sugeridos o utilizados:

- `name`
- `responsible_name`
- `category_id`
- `phone`
- `whatsapp_number`
- `description`
- `location_text`
- `profile_image_1920`
- `cover_image`
- `state`
- `portal_user_id`
- `onboarding_source`

Estados típicos:

- `draft`
- `pending`
- `approved`
- `rejected`
- `published`

---

## `whatsapp.bot.session`
Modelo para controlar la conversación del chatbot.

Campos sugeridos:

- `phone`
- `provider_id`
- `state`
- `last_message_at`
- `last_payload`
- `active`

Estados sugeridos:

- `start`
- `asking_business_name`
- `asking_responsible_name`
- `asking_category`
- `asking_phone`
- `asking_location`
- `asking_profile_photo`
- `completed`

---

## `tourism.portal.activation`
Modelo para administrar enlaces de activación.

Campos sugeridos:

- `provider_id`
- `user_id`
- `token`
- `expires_at`
- `used`

---

## `tourism.post`
Publicaciones del prestador dentro del portal.

Campos típicos:

- `author_id`
- `content`
- `image`
- `published`
- `create_date`

---

# Controladores

## `/whatsapp/webhook`
Webhook principal para Meta Cloud API.

### GET
Usado para la verificación inicial de Meta.

### POST
Recibe mensajes y eventos.

Responsabilidades:

- identificar número de teléfono
- localizar o crear sesión
- mover la máquina de estados
- guardar datos en Odoo
- descargar imágenes
- responder por WhatsApp

---

## `/tourism/activate/<token>`
Ruta pública para activar acceso web.

Responsabilidades:

- validar token
- verificar expiración
- permitir crear contraseña
- marcar token como usado
- redirigir al portal

---

## Rutas del portal
Estas rutas normalmente viven en `tourism_provider_portal`, pero este módulo se integra con ellas:

- perfil del prestador
- edición del perfil
- feed turístico
- creación de publicaciones

---

# Estructura sugerida del módulo

```text
whatsapp_turismo_bot/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   ├── whatsapp_webhook.py
│   └── portal_activation.py
├── models/
│   ├── __init__.py
│   ├── tourism_provider.py
│   ├── whatsapp_bot_session.py
│   ├── tourism_portal_activation.py
│   └── tourism_post.py
├── services/
│   ├── __init__.py
│   ├── whatsapp_service.py
│   ├── onboarding_service.py
│   └── media_service.py
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── views/
│   ├── tourism_provider_views.xml
│   ├── whatsapp_bot_session_views.xml
│   ├── tourism_portal_activation_views.xml
│   └── menu_views.xml
├── data/
│   ├── cron.xml
│   └── whatsapp_templates.xml
└── static/
    └── description/
        └── icon.png
