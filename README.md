# WinAudit.MajorERP

Servicio para cargar el mayor contable y el plan de cuentas exportado desde Contifico.

## Proposito
- Recepcionar archivos Excel por cliente y tenant.
- Guardar el archivo original.
- Registrar un lote de importacion.
- Cargar cuentas y movimientos en tablas contables.
- Dejar validaciones y trazabilidad para cruces futuros.

## Estructura inicial
- `app/api/`: endpoints
- `app/core/`: configuracion y logging
- `app/db/`: modelos y sesiones
- `app/parser/`: lectura y normalizacion del Excel
- `app/services/`: casos de uso
- `app/storage/`: rutas y guardado de archivos
- `app/workers/`: proceso asicrono

