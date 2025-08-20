from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from exiftracer.core import GeoSpy

console = Console()

def banner():
    console.print("""
[bold magenta]
██████╗ ███████╗ ██████╗ ███████╗ ██████╗ █████╗ ███╗   ██╗
██╔════╝ ██╔════╝██╔═══██╗██╔════╝██╔════╝██╔══██╗████╗  ██║
██║  ███╗█████╗  ██║   ██║███████╗██║     ███████║██╔██╗ ██║
██║   ██║██╔══╝  ██║   ██║╚════██║██║     ██╔══██║██║╚██╗██║
╚██████╔╝███████╗╚██████╔╝███████║╚██████╗██║  ██║██║ ╚████║
 ╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝
[/bold magenta]
:earth_africa: [bold cyan]ExifTracer - EXIF Analyzer MULTI[/bold cyan]
""")

def interactive_menu():
    banner_text = Text()
    banner_text.append("\n[*] ExifTracer Interactive Panel [*]\n")
    banner_text.append("[*] Escolha uma opção para começar: [*]\n\n")
    banner_text.append("[1] 🖼️  Analisar uma imagem\n")
    banner_text.append("[2] 📂  Analisar múltiplas imagens\n")
    banner_text.append("[0] ❌  Sair\n")

    panel = Panel(banner_text, title="ExifTracer", border_style="bright_magenta")
    console.print(panel, justify="center")

    choice = console.input("[bold cyan]Digite sua escolha ➜ [/bold cyan]")
    return choice

def main():
    spy = GeoSpy()
    while True:
        choice = interactive_menu()

        if choice == "1":
            image_path = console.input("[bold cyan]Digite o caminho da imagem ➜ [/bold cyan]")
            console.print(f"[bold green]Você escolheu analisar a imagem ➜[/bold green] {image_path}")
            result = spy.get_exif_gps(image_path)
            if result:
                geo_info = spy.reverse_geocode(result["latitude"], result["longitude"])
                result.update(geo_info)
                spy.show_geo(result)
                spy.create_map([result])
            else:
                console.print("[bold red]❌ Nenhuma informação de geolocalização encontrada na imagem[/bold red]")

        elif choice == "2":
            paths = console.input("[bold cyan]Digite os caminhos das imagens separados por vírgula ➜ [/bold cyan]")
            paths = [p.strip() for p in paths.split(",")]
            locations = []
            for img_path in paths:
                res = spy.get_exif_gps(img_path)
                if res:
                    geo_info = spy.reverse_geocode(res["latitude"], res["longitude"])
                    res.update(geo_info)
                    locations.append(res)
                    spy.show_geo(res)
                else:
                    console.print(f"[red]Nenhuma informação de geolocalização na imagem {img_path}[/red]")
            if locations:
                spy.create_map(locations)

        elif choice == "0":
            console.print("[bold red]Saindo...[/bold red]")
            break

if __name__ == "__main__":
    main()
