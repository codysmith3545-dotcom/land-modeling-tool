from __future__ import annotations

import json
from pathlib import Path


def write_interactive_map(path: Path, geojson: dict, title: str = "Land Modeling Tool") -> None:
    payload = json.dumps(geojson)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map {{ height: 100%; margin: 0; font-family: system-ui, sans-serif; }}
    .legend {{ background: white; padding: 10px 12px; line-height: 1.5; border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,.2); }}
    .legend i {{ width: 12px; height: 12px; display: inline-block; margin-right: 6px; border-radius: 50%; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const data = {payload};
    const map = L.map('map').setView([39.85, -86.15], 7);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap'
    }}).addTo(map);

    const colors = {{
      node: '#2563eb',
      historical_project: '#9333ea',
      parcel: '#16a34a',
    }};

    function parcelColor(p) {{
      if (p.buy_action === 'pursue_now') return '#15803d';
      if (p.buy_action === 'diligence') return '#ca8a04';
      if (p.buy_action === 'watch') return '#64748b';
      return '#94a3b8';
    }}

    const layers = {{ node: [], historical_project: [], parcel: [] }};
    data.features.forEach(f => {{
      const p = f.properties;
      const layer = p.layer;
      let marker;
      if (layer === 'parcel') {{
        marker = L.circleMarker([f.geometry.coordinates[1], f.geometry.coordinates[0]], {{
          radius: 6 + (p.buy_score || 0) * 6,
          color: parcelColor(p),
          fillColor: parcelColor(p),
          fillOpacity: 0.75,
          weight: 1,
        }});
      }} else {{
        marker = L.circleMarker([f.geometry.coordinates[1], f.geometry.coordinates[0]], {{
          radius: layer === 'node' ? 10 : 8,
          color: colors[layer],
          fillColor: colors[layer],
          fillOpacity: 0.85,
          weight: 2,
        }});
      }}
      const popup = Object.entries(p).map(([k,v]) => `<b>${{k}}</b>: ${{v}}`).join('<br/>');
      marker.bindPopup(`<div style="max-width:240px;font-size:13px">${{popup}}</div>`);
      marker.addTo(map);
      layers[layer].push(marker);
    }});

    const legend = L.control({{ position: 'bottomright' }});
    legend.onAdd = () => {{
      const div = L.DomUtil.create('div', 'legend');
      div.innerHTML = `
        <strong>{title}</strong><br/>
        <i style="background:#2563eb"></i>Infrastructure node<br/>
        <i style="background:#9333ea"></i>Historical project<br/>
        <i style="background:#15803d"></i>Pursue now<br/>
        <i style="background:#ca8a04"></i>Diligence<br/>
        <i style="background:#64748b"></i>Watch / pass
      `;
      return div;
    }};
    legend.addTo(map);
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
