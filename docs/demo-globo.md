# Demo pública del globo inmersivo

URL: https://hexastra-globo-inmersivo.pages.dev/

Proyecto de Pages: `hexastra-globo-inmersivo`. Su rama de producción en Cloudflare es `mbasilico-resh/ux-globo-inmersivo`. Usa su propio namespace KV, definido en `pages/wrangler.globo.toml`.

Publicar el front del worktree actual:

```bash
HEXASTRA_PAGES_CONFIG=pages/wrangler.globo.toml ./scripts/deploy_pages.sh
```

Mantener abiertas las APIs y los túneles desde este worktree (puertos exclusivos de esta demo):

```bash
HEXASTRA_PAGES_CONFIG=pages/wrangler.globo.toml PLANETARY_PORT=19522 EARTH_PORT=19523 ./scripts/share.sh https://hexastra-globo-inmersivo.pages.dev
```

El comando actualiza el proxy del proyecto nuevo. Los enlaces públicos de las APIs son `/api/planetary` y `/api/earth` sobre el mismo dominio; no hace falta compartir parámetros ni direcciones locales. Al reiniciar los túneles, el comando actualiza sus URLs en KV y se conserva el enlace del front.

El front queda alojado en Cloudflare. Las APIs corren en esta Mac: para probar datos y comparativas, la Mac tiene que permanecer encendida, conectada y con el terminal de `share.sh` abierto. Cerrar ese terminal corta solo los servicios y túneles que inició ese comando.

La demo actual consulta la base ya integrada en modo de solo lectura. Antes de arrancar los servicios, se carga la configuración privada de esta Mac:

```bash
source ~/.config/hexastra/globo-inmersivo-demo.env
HEXASTRA_PAGES_CONFIG=pages/wrangler.globo.toml PLANETARY_PORT=19522 EARTH_PORT=19523 ./scripts/share.sh https://hexastra-globo-inmersivo.pages.dev
```

Esa configuración contiene la conexión fuera del repositorio y activa `default_transaction_read_only=on`. El arranque no carga ni exporta la base compartida. `/api/earth/health` y `/api/planetary/health` informan `catalog_origin: postgres` para distinguir este catálogo del archivo base.
