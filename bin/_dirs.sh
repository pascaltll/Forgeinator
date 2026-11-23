# v3.15 · Carpetas de esta copia (lo incluyen bin/hub y bin/hub-browser). Debe dar lo mismo que hub/channel.py:layout().
#   Sin archivo CHANNEL (instalación antigua):  todo en $D/data
#   Con CHANNEL=stable|dev:                     biblioteca común ~/.local/share/forgeinator, registros ~/.local/state/forgeinator/<canal>
# Entrada: D (carpeta del programa). Salida: HUB_CH, DATA_DIR, STATE_DIR.
HUB_CH="${HUB_CHANNEL:-}"
[ -z "$HUB_CH" ] && [ -f "$D/CHANNEL" ] && HUB_CH="$(tr -dc 'a-z' < "$D/CHANNEL")"
case "$HUB_CH" in stable|dev) ;; *) HUB_CH="";; esac
if [ -n "${HUB_DATA:-}" ]; then
  DATA_DIR="$HUB_DATA"; STATE_DIR="${HUB_STATE:-$HUB_DATA}"
elif [ -n "$HUB_CH" ]; then
  DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/forgeinator"
  STATE_DIR="${HUB_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/forgeinator/$HUB_CH}"
else
  DATA_DIR="$D/data"; STATE_DIR="${HUB_STATE:-$D/data}"
fi
