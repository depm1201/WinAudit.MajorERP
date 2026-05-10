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

## Autenticacion

Todos los endpoints de este servicio requieren un token JWT Bearer valido. El endpoint `GET /health` es publico (usado por Docker healthcheck).

El token es emitido por el backend .NET (`WinAudit.Backend`) y validado aqui usando la misma clave simetrica (HS256). El Gateway lo verifica antes de hacer proxy, pero el servicio tambien lo valida por su cuenta como segunda capa.

- Sin token o con token invalido: `403 Forbidden`
- Con token expirado: `401 Unauthorized`
- La clave se lee desde la variable de entorno `JWT_SECRET`

Este servicio NO debe ser consumido directamente por el backend .NET. El flujo correcto es:

```
Frontend -> Gateway -> WinAudit.MajorERP
```

