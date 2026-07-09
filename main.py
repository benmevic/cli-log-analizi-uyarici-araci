import csv
import importlib.util
import json
import os
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

os.chdir(os.path.dirname(os.path.abspath(__file__)))

console = Console()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ZAMAN_DAMGASI = time.strftime("%d_%m_%Y_%H%M%S")
LOG_DOSYA_ISMI = os.path.join(OUTPUT_DIR, f"rapor_{ZAMAN_DAMGASI}.csv")
PLUGINS_DIR = "plugins"


def load_rules():
    try:
        with open("rules.json", "r", encoding="utf-8") as f:
            return json.load(f)["rules"]
    except Exception as e:
        console.print(f"[bold red]Hata:[/bold red] rules.json okunamadi! {e}")
        return []


def save_to_csv(log_data, _dosya=LOG_DOSYA_ISMI):
    file_exists = os.path.isfile(_dosya)
    with open(_dosya, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        if not file_exists:
            writer.writerow(["Zaman", "Kategori", "Etiket", "Dosya Yolu", "Mesaj"])
        writer.writerow(log_data)


def load_plugins():
    plugins = {}
    if not os.path.isdir(PLUGINS_DIR):
        return plugins

    for filename in sorted(os.listdir(PLUGINS_DIR)):
        if filename.endswith(".py") and not filename.startswith("_"):
            plugin_path = os.path.join(PLUGINS_DIR, filename)
            module_name = filename[:-3]
            try:
                spec = importlib.util.spec_from_file_location(module_name, plugin_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "PLUGIN_NAME") and hasattr(module, "run"):
                    plugins[module_name] = module
                    console.print(
                        f"[dim green][+] Plugin yuklendi:[/dim green] "
                        f"[bold]{module.PLUGIN_NAME}[/bold]"
                    )
            except Exception as e:
                console.print(f"[bold red]Plugin yukleme hatasi ({filename}):[/bold red] {e}")

    return plugins


def analyze_log(file_path):
    if not os.path.exists(file_path):
        console.print(f"[bold red]Hata:[/bold red] '{file_path}' dosyasi bulunamadi!")
        return

    rules = load_rules()
    stats = {"KRITIK": 0, "HATA": 0, "BILGI": 0, "GUVENLIK": 0}
    total_lines = 0
    console.print(f"\n[bold yellow][*][/bold yellow] {file_path} analiz ediliyor...", style="italic")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                total_lines += 1
                for rule in rules:
                    if rule["keyword"].lower() in line.lower():
                        kat = rule.get("kategori", "BILGI")
                        stats[kat] = stats.get(kat, 0) + 1
                        save_to_csv(
                            [
                                time.strftime("%Y-%m-%d %H:%M:%S"),
                                kat,
                                rule["label"],
                                file_path,
                                line.strip(),
                            ]
                        )
                        break

        table = Table(title=f"\n[bold green]Analiz Ozeti: {file_path}[/bold green]")
        table.add_column("Kategori", style="bold")
        table.add_column("Adet", justify="right", style="magenta")
        for kat, count in stats.items():
            if count > 0:
                table.add_row(kat, str(count))

        unmatched = total_lines - sum(stats.values())
        table.add_section()
        table.add_row("Kategorize Edilemeyen", str(unmatched), style="dim")
        table.add_row("Toplam Satir", str(total_lines), style="bold cyan")
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Hata:[/bold red] {e}")


def main_menu():
    plugins = load_plugins()

    menu_items = {"1": ("Tekli Dosya Analizi", None)}

    for idx, (_, plugin) in enumerate(plugins.items(), start=2):
        desc = getattr(plugin, "PLUGIN_DESC", plugin.PLUGIN_NAME)
        menu_items[str(idx)] = (desc, plugin)

    exit_key = str(len(menu_items) + 1)
    menu_items[exit_key] = ("Cikis", None)

    while True:
        menu_text = ""
        for key, (label, _) in menu_items.items():
            menu_text += f"[bold cyan]{key}.[/bold cyan] {label}\n"

        console.print(
            "\n",
            Panel.fit(
                menu_text.strip(),
                title="LOG ANALIZ SISTEMI",
                border_style="blue",
            ),
        )

        choice = console.input("[bold yellow]Seciminiz: [/bold yellow]").strip()

        if choice not in menu_items:
            console.print("[bold red]Gecersiz secim![/bold red]")
            continue

        _, plugin = menu_items[choice]

        if choice == exit_key:
            break
        elif choice == "1":
            path = console.input("Dosya yolu: ", markup=False).strip() or "logs/log1.txt"
            analyze_log(path)
        elif plugin is not None:
            plugin.run(console, load_rules, save_to_csv)


if __name__ == "__main__":
    main_menu()
