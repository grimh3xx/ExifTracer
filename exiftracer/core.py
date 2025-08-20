from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import folium
import requests
from rich.console import Console
from rich.table import Table

console = Console()

class GeoSpy:
    def get_exif_gps(self, image_path: str) -> dict:
        try:
            img = Image.open(image_path)
            exif_data = img._getexif()
            if not exif_data:
                return {}
            gps_info = {}
            for tag, value in exif_data.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_info[sub_decoded] = value[t]
            if not gps_info:
                return {}
            return self._gps_to_decimal(gps_info)
        except Exception as e:
            console.print(f"[red]Erro ao ler EXIF: {e}[/red]")
            return {}

    def _gps_to_decimal(self, gps_data: dict) -> dict:
        try:
            def convert(value):
                d, m, s = value
                return float(d) + float(m)/60 + float(s)/3600
            lat = convert(gps_data['GPSLatitude'])
            lon = convert(gps_data['GPSLongitude'])
            if gps_data['GPSLatitudeRef'] == 'S':
                lat = -lat
            if gps_data['GPSLongitudeRef'] == 'W':
                lon = -lon
            return {"latitude": lat, "longitude": lon}
        except Exception:
            return {}

    def reverse_geocode(self, lat, lon) -> dict:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"lat": lat, "lon": lon, "format": "jsonv2"}
        headers = {"User-Agent": "ExifTracer"}
        try:
            response = requests.get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                addr = data.get("address", {})
                return {
                    "address": data.get("display_name"),
                    "road": addr.get("road"),
                    "suburb": addr.get("suburb"),
                    "city": addr.get("city") or addr.get("town") or addr.get("village"),
                    "state": addr.get("state"),
                    "country": addr.get("country"),
                    "postcode": addr.get("postcode")
                }
            else:
                return {"error": "Falha no geocoding"}
        except Exception as e:
            return {"error": f"Falha no geocoding: {e}"}

    def create_map(self, locations: list, map_file: str = "map.html"):
        if not locations:
            console.print("[red]Nenhuma localização para mostrar no mapa[/red]")
            return
        loc0 = locations[0] if 'latitude' in locations[0] else {'latitude':0,'longitude':0}
        m = folium.Map(location=[loc0['latitude'], loc0['longitude']], zoom_start=15)
        for idx, loc in enumerate(locations, 1):
            if 'latitude' in loc and 'longitude' in loc:
                tooltip = loc.get("address") or f"Imagem {idx}"
                folium.Marker(
                    [loc['latitude'], loc['longitude']],
                    tooltip=tooltip
                ).add_to(m)
        m.save(map_file)
        console.print(f"[green]Mapa salvo em {map_file} com {len(locations)} pontos[/green]")
        import webbrowser
        webbrowser.open(map_file)

    def show_geo(self, geo: dict):
        table = Table(title="Dados de Geolocalização")
        table.add_column("Campo", style="cyan", no_wrap=True)
        table.add_column("Valor", style="magenta")
        for k, v in geo.items():
            table.add_row(str(k), str(v))
        console.print(table)
