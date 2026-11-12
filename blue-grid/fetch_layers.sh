#!/usr/bin/env bash
# Download the PNG layers Earth Engine printed, into data/<city>/.
#
#   1. Run gee_blue_grid.js, copy every "PNG <name>: https://..." console line
#      into urls/<city>.txt (one per line, any surrounding text is tolerated).
#   2. ./fetch_layers.sh <city>
#
# Earth Engine thumbnail URLs expire, so re-copy them if a download 404s.
set -u
CITY="${1:-bengaluru}"
SRC="urls/${CITY}.txt"
DEST="data/${CITY}"

[ -f "$SRC" ] || { echo "missing $SRC — paste the PNG lines from the Earth Engine console into it"; exit 1; }
mkdir -p "$DEST"

ok=0; fail=0
while IFS= read -r line; do
  url=$(printf '%s' "$line" | grep -oE 'https://[^ "]+' | head -1)
  [ -z "$url" ] && continue
  # Layer name is the word just before the colon, e.g. "PNG rgb2005: https://..."
  # Anchored on any scheme, not the literal "https". Anchored on https, a line
  # carrying any other URL left the whole URL as the name, and the part file
  # built from it then contained slashes and curl failed to write it at all.
  name=$(printf '%s' "$line" | sed -E 's/[[:space:]]*:[[:space:]]*[a-zA-Z][a-zA-Z0-9+.-]*:\/\/.*$//' | awk '{print $NF}')
  [ -z "$name" ] && continue
  # The keyword the console line starts with decides the extension and how the
  # download is checked. GEOJSON lines carry the ranked building layer, which
  # used to be reachable only through a Drive export task — start it, wait,
  # find the file, rename it, move it. That friction is why the layer was still
  # missing long after every raster had landed, and the tool degrades quietly
  # enough without it that the cost of never doing it stayed invisible.
  kind=$(printf '%s' "$line" | awk '{print $1}' | tr '[:lower:]' '[:upper:]')
  case "$kind" in
    GEOJSON) ext=geojson ;;
    *)       ext=png ;;
  esac
  # Staged through a part file, because the normal way to use this script is
  # to re-run it after ONE new layer was added, with every other URL in the
  # list long expired. Downloading straight onto the destination meant a 404
  # truncated a layer that was already on disk and correct: the fetch reported
  # a failure and silently destroyed the evidence at the same time.
  part="$DEST/.$name.$ext.part"
  # A PNG is checked by its magic bytes; GeoJSON has none, so it is checked by
  # parsing. Either way an Earth Engine error page is HTML and fails both, which
  # is the case that matters — it arrives with a 200 and looks like a download.
  if curl -sSfL -o "$part" "$url" \
     && { [ "$ext" = geojson ] \
          && python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get("type")=="FeatureCollection" else 1)' "$part" \
          || { [ "$ext" = png ] && file "$part" | grep -q 'PNG image'; }; }; then
    mv -f "$part" "$DEST/$name.$ext"
    n=''
    [ "$ext" = geojson ] && n=" ($(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["features"]))' "$DEST/$name.$ext") features)"
    printf '  ok    %-12s %s%s\n' "$name" "$(du -h "$DEST/$name.$ext" | cut -f1)" "$n"
    ok=$((ok+1))
  else
    rm -f "$part"
    if [ -f "$DEST/$name.$ext" ]; then
      printf '  skip  %-12s URL expired; kept the copy already on disk\n' "$name"
    else
      printf '  FAIL  %-12s download failed and nothing on disk\n' "$name"
    fi
    fail=$((fail+1))
  fi
done < "$SRC"
echo "$ok downloaded, $fail failed -> $DEST"

# Earth Engine writes a fractional alpha wherever a layer mixes source scales,
# and a browser's canvas quantisation-damages every channel underneath it.
# Flattening here means a freshly fetched layer is never briefly wrong.
if [ -x ./flatten_alpha.py ]; then ./flatten_alpha.py "$CITY"; fi
