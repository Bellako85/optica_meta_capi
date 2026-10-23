# Óptica Meta CAPI

Integración de **Odoo 17** con **Meta Conversions API**, desarrollada para Óptica Zamora. Permite enviar señales comerciales desde CRM, citas y ventas, con configuración centralizada y seguimiento de los envíos en cada registro.

La implementación principal utiliza `requests` y el modelo auxiliar `meta.capi.mixin`. La versión declarada del módulo es `17.0.1.0.0`.

> Esta documentación describe el código del repositorio. La descripción del manifiesto conserva referencias a automatismos anteriores: los flujos activos documentados abajo se ejecutan mediante botones o llamadas explícitas a sus métodos.

## Eventos y condiciones de envío

| Área | Botón | Evento enviado | Condiciones |
| --- | --- | --- | --- |
| CRM | Enviar Contact a Meta | `Contact` | Oportunidad en la etapa con ID interno `2`, cliente vinculado y envío pendiente. |
| Citas | Enviar Schedule a Meta | `Schedule_Manual` | Cita de origen `backend`, estado `confirmed` y envío pendiente. |
| Ventas | Enviar Purchase a Meta | `Purchase` | Orden en `sale` o `done`, envío pendiente y al menos una factura publicada cuyo saldo pendiente sea menor que su total. |

### CRM

El método `action_send_contact_to_meta()` toma los datos del cliente vinculado y utiliza el identificador `contact_{lead.id}`. El origen del evento es `system_generated`.

La etapa **Calificado** está vinculada al **ID interno 2** tanto en Python como en la vista. Cambiar el nombre de una etapa no cambia su ID; una base nueva debe revisar esta correspondencia antes de utilizar el botón.

### Citas

El método `action_send_schedule_to_meta()` envía el evento personalizado **`Schedule_Manual`**, aunque el botón muestre “Enviar Schedule a Meta”. Utiliza `schedule_manual_{appointment.id}` y `action_source=system_generated`.

Las citas web están excluidas de este envío manual. Su flujo de confirmación y el evento `Schedule` deben revisarse en el módulo dependiente [optica_appointment](https://github.com/Bellako85/optica_appointment).

Los datos de contacto se obtienen del `partner_id`; no se extraen directamente de los campos de texto de la cita. Los valores de navegador guardados en la cita se incluyen cuando existen. Una cita creada desde backend puede no tener cookies, IP o agente de usuario del paciente.

### Ventas

El método `action_send_purchase_to_meta()` envía:

- `value`: total completo de la orden, incluso si solo existe un anticipo.
- `currency`: moneda de la orden; usa `MXN` como respaldo.
- `order_id`: referencia de la orden.
- `event_id`: `purchase_{order.id}`.

La comprobación de pago se basa en `invoice.state == 'posted'` y `amount_residual < amount_total`; no exige que la orden esté totalmente pagada.

El origen se determina mediante `x_meta_order_link_opened`: `website` si está marcado y `physical_store` en caso contrario. Es una clasificación implementada en el módulo, no una comprobación independiente del canal real de compra.

El método admite otro `event_name` por código. Para eventos distintos de `Purchase` no aplica las validaciones de compra ni guarda el indicador de compra enviada; mantiene el formato de ID `purchase_{order.id}`. No existe un disparador automático de `InitiateCheckout` en este repositorio.

## Requisitos

- Odoo 17 y acceso a su directorio de addons personalizados.
- Módulos declarados: `base`, `web`, `website`, `website_sale`, `crm`, `sale`, `mail` y `optica_appointment`.
- Una versión compatible de `optica_appointment`, con sus campos y vistas heredados por esta integración.
- Biblioteca Python `requests` disponible en el entorno de Odoo.
- Pixel ID y token de acceso de Meta apropiados para el envío de eventos.
- Conectividad saliente HTTPS hacia `graph.facebook.com`.

El emisor principal tiene fijada la versión **`v23.0`** de Graph API y un tiempo de espera de **20 segundos** por solicitud. Estos valores están en [models/meta_capi.py](models/meta_capi.py).

## Instalación

> Antes de instalar desde cero, revisa las observaciones de integración indicadas al final. El manifiesto referencia un archivo JavaScript que no está incluido en el árbol actual.

1. Instala la dependencia [optica_appointment](https://github.com/Bellako85/optica_appointment).
2. Clona este repositorio dentro de un directorio incluido en `addons_path`, conservando el nombre técnico:

   ```bash
   cd /ruta/a/custom-addons
   git clone https://github.com/Bellako85/optica_meta_capi.git optica_meta_capi
   ```

3. Reinicia Odoo para cargar el código.
4. Activa el modo desarrollador y actualiza la lista de aplicaciones.
5. Busca **Optica Meta CAPI** e instálalo. Si no aparece, elimina el filtro “Aplicaciones”: el manifiesto declara `application=False`.
6. Abre **Ajustes → Meta CAPI** y guarda la configuración.

Para actualizar una instalación existente, utiliza el procedimiento habitual de actualización de módulos de tu servidor. Valida primero en una base de pruebas.

## Configuración

| Campo en Ajustes | Parámetro técnico | Uso |
| --- | --- | --- |
| Enable Meta CAPI | `optica_meta_capi.meta_capi_enabled` | Activa el emisor principal. |
| Meta Pixel ID | `optica_meta_capi.meta_pixel_id` | Identificador de destino. |
| Meta Access Token | `optica_meta_capi.meta_access_token` | Credencial de acceso a la API. |
| Meta Test Event Code | `optica_meta_capi.meta_test_event_code` | Código opcional para pruebas de eventos. |

Los parámetros se almacenan en `ir.config_parameter`; esta implementación no define una configuración independiente por compañía o sitio web.

Si la integración está desactivada o faltan Pixel ID o token, el emisor devuelve `skipped`. Los botones interpretan ese resultado como un envío no completado y muestran un error al usuario.

## Identificación y seguimiento

El auxiliar construye `user_data` con los datos disponibles:

| Dato | Tratamiento en el código |
| --- | --- |
| Email | Recorte de espacios externos, minúsculas y SHA-256. |
| Teléfono | Solo dígitos; añade `52` si no comienza con ese prefijo; después aplica SHA-256. |
| Nombre y apellido | SHA-256 cuando se pasan explícitamente al auxiliar. |
| `external_id` | ID del contacto como texto, sin hash en esta implementación. |
| `fbp`, `fbc`, IP y agente de usuario | Se incluyen sin hash cuando están disponibles. |

**SHA-256 es hashing, no cifrado reversible.** La normalización telefónica está orientada a México; no debe asumirse válida para números de otros países.

Después de un resultado sin `error` ni `skipped`, cada flujo principal guarda su indicador de envío y su ID de evento. El botón correspondiente se oculta y el método bloquea un nuevo envío del mismo registro.

Esto es un control local: el código registra `events_received`, pero no exige que sea mayor que cero antes de marcar el envío. La recepción debe verificarse también en Meta.

Los IDs estables permiten coordinar la deduplicación con otras implementaciones. Este repositorio, por sí solo, no garantiza que Pixel y CAPI envíen el mismo nombre e ID de evento.

## Portal y señales del navegador

[controllers/portal_meta.py](controllers/portal_meta.py) contiene una extensión del portal de pedidos para guardar:

- Apertura del enlace y fecha.
- Cookies `_fbp` y `_fbc`, si existen.
- IP y agente de usuario.
- Ruta de origen `/my/orders/{id}`, sin el token de acceso.

El nombre del campo “Link Abierto en WhatsApp” no demuestra procedencia de WhatsApp: el código pretende registrar la visita al portal, independientemente del canal por el que se compartió.

**Pendiente de validación en Odoo 17:** la sobrescritura de `portal_my_order` no incluye un decorador de ruta. No debe darse por comprobada la captura del portal solo por la existencia de estos campos. Además, la URL guardada es relativa y la cabecera `X-Forwarded-For` se copia completa si está presente.

## Prueba funcional

Utiliza registros de prueba y un **Meta Test Event Code**.

1. Activa la integración, configura las credenciales y guarda.
2. **CRM:** vincula un contacto a una oportunidad en la etapa ID 2 y pulsa “Enviar Contact a Meta”.
3. **Citas:** confirma una cita de origen backend con contacto vinculado y pulsa “Enviar Schedule a Meta”. Busca **`Schedule_Manual`**.
4. **Ventas:** confirma una orden con una factura publicada que tenga pago o anticipo y pulsa “Enviar Purchase a Meta”.
5. Comprueba en Odoo los indicadores e IDs y verifica en Meta el nombre del evento, su recepción y, para compras, valor y moneda.
6. Verifica que los botones de registros enviados dejan de mostrarse y que los métodos rechazan nuevos envíos.
7. Para el portal, abre un enlace autorizado con datos de prueba y revisa si se guardan realmente las señales descritas arriba.
8. Retira el código de prueba antes de la operación normal.

La confirmación de una venta, el cambio de etapa o la confirmación de una cita **no ejecutan automáticamente estos botones** en el código activo revisado.

## Diagnóstico

| Situación | Qué revisar |
| --- | --- |
| No aparece el botón de CRM | ID real de la etapa e indicador `x_meta_contact_sent`. |
| No aparece el botón de citas | Origen `backend`, estado `confirmed` e indicador `x_meta_schedule_sent`. |
| Purchase rechaza el envío | Estado de venta y existencia de una factura publicada con saldo menor que su total. |
| El envío devuelve error | Activación, Pixel ID, token, conectividad y respuesta de Meta en los logs. |
| Meta no muestra el evento esperado | Distinguir `Contact`, `Schedule_Manual` y `Purchase`; revisar código de prueba y `events_received`. |
| Faltan cookies o datos del navegador | Confirmar si hubo visita web y si la captura del portal funciona; los registros backend no los generan por sí mismos. |
| Error de assets | Revisar la referencia a `static/src/js/meta_pixel.js`, ausente en el repositorio actual. |

Los mensajes del emisor principal llevan el prefijo `META CAPI`. Los envíos son síncronos; no hay una cola ni reintentos automáticos implementados en este módulo.

## Datos y operación

El código registra payloads y respuestas en los logs, que pueden contener hashes de contacto, identificadores, IP, cookies y otros metadatos. Restringe su acceso y evita publicar logs completos o credenciales. El token se envía como parámetro de la solicitud; revisa también posibles URLs incluidas en registros de errores antes de compartirlos.

Esta integración no implementa por sí misma un mecanismo de consentimiento. Su uso debe coordinarse con la configuración de privacidad y medición del sitio. No incluyas diagnósticos, graduaciones ni notas clínicas en eventos publicitarios.

## Estructura

| Ruta | Responsabilidad |
| --- | --- |
| `models/meta_capi.py` | Configuración, normalización, hashing y envío HTTP. |
| `models/res_config_settings.py` | Campos de Ajustes. |
| `models/crm_lead.py` | Envío manual de Contact. |
| `models/optica_appointment.py` | Envío manual de Schedule_Manual. |
| `models/sale_order.py` | Purchase y señales asociadas al pedido. |
| `controllers/portal_meta.py` | Captura prevista de visitas al portal. |
| `views/` | Ajustes, botones e indicadores de envío. |
| `wizard/mail_compose_message.py` | Implementación de envío de Schedule por correo, actualmente no importada. |

## Observaciones de integración

- **Asset ausente:** el manifiesto declara `optica_meta_capi/static/src/js/meta_pixel.js`, pero el archivo no aparece en el árbol actual. No se debe presentar este módulo como una instalación completa de Pixel en navegador.
- **Asistente de correo inactivo:** la importación de `mail_compose_message` está comentada en `wizard/__init__.py`. El archivo utiliza `facebook_business`, pero esa dependencia no participa en el flujo activo. Reactivarlo requiere revisar su compatibilidad y sus campos.
- **Etapa fija:** el ID 2 de CRM es una particularidad de la base original.
- **Portal:** comprobar publicación de la ruta, captura efectiva, formato de IP y URL de origen antes de depender de esas señales.
- **Manifiesto:** su descripción de Lead automático, Schedule al enviar correo y Purchase al confirmar presupuesto no refleja los flujos activos documentados aquí.

Estas observaciones describen el repositorio y no sustituyen una prueba sobre la instancia desplegada.

## Licencia

Este módulo se distribuye bajo **GNU LGPL v3** (SPDX: `LGPL-3.0-only`), coherente con el valor `LGPL-3` de [__manifest__.py](__manifest__.py).

[LICENSE](LICENSE) incluye el texto completo de LGPL v3 y de GPL v3, cuyos términos incorpora LGPL. La inclusión de ambos textos no representa dos licencias alternativas.

---

Desarrollado por **Bellako85** para [Óptica Zamora](https://optica-zamora.com).
