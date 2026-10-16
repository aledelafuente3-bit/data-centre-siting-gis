#!/bin/bash
# Wait for all 7 NFHL SFHA GeoJSON files to be populated (> 100 KB),
# then automatically run step2b_nfhl_process.py.
# Run this in background after launching step2_nfhl_retry_failed.py.

NFHL_DIR="/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/07_hazards/raw/flood/nfhl"
QPYTHON="/Applications/QGIS-LTR.app/Contents/MacOS/bin/python3"
SCRIPT_DIR="/Users/ale/Documents/Sustainable_Data_Center_Siting_GIS/13_scripts"
LOG="/tmp/step2b_nfhl_process.log"

STATES="az ia il or tx va wv"

echo "=== Waiting for all 7 NFHL SFHA files ==="
echo "Started: $(date)"

while true; do
    all_ready=true
    for state in $STATES; do
        f="${NFHL_DIR}/nfhl_sfha_${state}.geojson"
        if [ ! -f "$f" ] || [ "$(wc -c < "$f")" -lt 100000 ]; then
            all_ready=false
            echo "  $(date '+%H:%M:%S') Waiting: $state not ready yet ($(wc -c < "$f" 2>/dev/null || echo 0) bytes)"
            break
        fi
    done

    if $all_ready; then
        echo ""
        echo "=== All 7 SFHA files ready — launching step2b at $(date) ==="
        for state in $STATES; do
            f="${NFHL_DIR}/nfhl_sfha_${state}.geojson"
            sz=$(wc -c < "$f")
            echo "  $state: $(echo "scale=1; $sz/1048576" | bc) MB"
        done
        echo ""
        cd /Users/ale/Documents/Sustainable_Data_Center_Siting_GIS
        $QPYTHON 13_scripts/step2b_nfhl_process.py 2>&1 | tee "$LOG"
        echo ""
        echo "=== step2b complete at $(date) ==="
        exit 0
    fi

    # Check every 60 seconds
    sleep 60
done
