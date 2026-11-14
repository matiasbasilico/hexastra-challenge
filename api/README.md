# API monolítica (deprecada)

El backend se partió en dos microservicios:

- `services/planetary/` — puerto 8766
- `services/earth/` — puerto 8767

El front estático se sirve en el puerto 8765 (`./run_all.sh`).

Este directorio se deja solo como referencia del prototipo anterior (`GET /similar`).
No lo uses para el buscador TASI ni para el catálogo mundial.
