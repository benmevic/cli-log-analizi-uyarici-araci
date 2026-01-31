import time
import json
import csv
import os
from collections import deque
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.live import Live
from rich.layout import Layout

console = Console()

#çıktı dizini ve log dosyası ayarları
OUTPUT_DIR = "outputs"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

ZAMAN_DAMGASI = time.strftime('%d_%m_%Y_%H%M%S')
LOG_DOSYA_ISMI = os.path.join(OUTPUT_DIR, f"rapor_{ZAMAN_DAMGASI}.csv")

def load_rules():
    try:
        with open('rules.json', 'r') as f:
            return json.load(f)['rules']
    except Exception as e:
        console.print(f"[bold red]Hata:[/bold red] rules.json okunamadı! {e}")
        return []

def save_to_csv(log_data):
    file_exists = os.path.isfile(LOG_DOSYA_ISMI)
    with open(LOG_DOSYA_ISMI, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        if not file_exists:
            writer.writerow(['Zaman', 'Kategori', 'Etiket', 'Dosya Yolu', 'Mesaj'])
        writer.writerow(log_data)

def make_stats_columns(stats_dict):
    return Columns([
        Panel(f"[bold red]KRITIK: {stats_dict['KRITIK']}[/bold red]", border_style="red"),
        Panel(f"[bold orange1]HATA: {stats_dict['HATA']}[/bold orange1]", border_style="orange1"),
        Panel(f"[bold green]BILGI: {stats_dict['BILGI']}[/bold green]", border_style="green"),
        Panel(f"[bold cyan]GUVENLIK: {stats_dict.get('GUVENLIK', 0)}[/bold cyan]", border_style="cyan"),
    ])

#tek dosya analiz fonksiyonu
def analyze_log(file_path):
    if not os.path.exists(file_path):
        console.print(f"[bold red]Hata:[/bold red] '{file_path}' dosyası bulunamadı!")
        return

    rules = load_rules()
    stats = {"KRITIK": 0, "HATA": 0, "BILGI": 0, "GUVENLIK": 0}
    total_lines = 0
    console.print(f"\n[bold yellow][*][/bold yellow] {file_path} analiz ediliyor...", style="italic")
    
    try:
        with open(file_path, 'r', errors='ignore') as f:
            for line in f:
                total_lines += 1
                for rule in rules:
                    if rule['keyword'].lower() in line.lower():
                        kat = rule.get('kategori', 'BILGI')
                        stats[kat] = stats.get(kat, 0) + 1
                        save_to_csv([time.strftime('%Y-%m-%d %H:%M:%S'), kat, rule['label'], file_path, line.strip()])
                        break
        
        table = Table(title=f"\n[bold green]Analiz Özeti: {file_path}[/bold green]")
        table.add_column("Kategori", style="bold")
        table.add_column("Adet", justify="right", style="magenta")
        for kat, count in stats.items():
            if count > 0: table.add_row(kat, str(count))
            
        unmatched = total_lines - sum(stats.values())
        table.add_section()
        table.add_row("Kategorize Edilemeyen", str(unmatched), style="dim")
        table.add_row("Toplam Satır", str(total_lines), style="bold cyan")
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Hata:[/bold red] {e}")

#toplu dosya analiz fonksiyonu
def analyze_directory(dir_path):
    if not os.path.isdir(dir_path):
        console.print(f"[bold red]Hata:[/bold red] '{dir_path}' geçerli bir klasör değil!")
        return

    rules = load_rules()
    grand_stats = {"KRITIK": 0, "HATA": 0, "BILGI": 0, "GUVENLIK": 0}
    file_count = 0
    total_lines_global = 0
    console.print(f"\n[bold yellow][*][/bold yellow] {dir_path} taranıyor...", style="italic")
    
    for root, dirs, files in os.walk(dir_path):
        for name in files:
            if name.endswith(('.gz', '.zip', '.tar', '.1', '.old')): continue
            file_path = os.path.join(root, name)
            file_count += 1
            try:
                with open(file_path, 'r', errors='ignore') as f:
                    for line in f:
                        total_lines_global += 1
                        for rule in rules:
                            if rule['keyword'].lower() in line.lower():
                                kat = rule.get('kategori', 'BILGI')
                                grand_stats[kat] += 1
                                save_to_csv([time.strftime('%Y-%m-%d %H:%M:%S'), kat, rule['label'], file_path, line.strip()])
                                break
            except: continue

    table = Table(title=f"\n[bold green]TOPLU ANALİZ RAPORU: {dir_path}[/bold green]")
    table.add_column("Kategori", style="bold")
    table.add_column("Toplam Adet", justify="right", style="magenta")
    for kat, count in grand_stats.items():
        if count > 0: table.add_row(kat, str(count))
    
    unmatched_global = total_lines_global - sum(grand_stats.values())
    table.add_section()
    table.add_row("Tanımlanamayan (Tüm Dosyalar)", str(unmatched_global), style="dim")
    table.add_row("Toplam Satır (Genel)", str(total_lines_global), style="bold cyan")
    console.print(table)

#tail mode fonksiyonu
def tail_log(file_path):
    if not os.path.exists(file_path):
        console.print(f"[bold red]Hata:[/bold red] '{file_path}' bulunamadı!")
        return

    rules = load_rules()
    live_stats = {"KRITIK": 0, "HATA": 0, "BILGI": 0, "GUVENLIK": 0}
    log_queue = deque(maxlen=15)
    
    layout = Layout()
    layout.split_column(Layout(name="ust", size=5), Layout(name="alt"))

    console.clear()

    with Live(layout, refresh_per_second=4, screen=True) as live:
        try:
            with open(file_path, 'r', errors='ignore') as f:
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(0.4); continue
                    
                    for rule in rules:
                        if rule['keyword'].lower() in line.lower():
                            kat = rule.get('kategori', 'BILGI')
                            live_stats[kat] += 1
                            
                            color = "red" if kat in ["KRITIK", "HATA"] else "green"
                            if kat == "GUVENLIK": color = "cyan"
                            
                            log_queue.append(f"[[blue]{time.strftime('%H:%M:%S')}[/blue]] [[bold {color}]{rule['label']}[/bold {color}]] {line.strip()}")
                            layout["ust"].update(make_stats_columns(live_stats))
                            layout["alt"].update(Panel("\n".join(list(log_queue)), title="[white]CANLI LOG AKIŞI[/white]", border_style="blue"))
                            save_to_csv([time.strftime('%Y-%m-%d %H:%M:%S'), kat, rule['label'], file_path, line.strip()])
                            break
        except KeyboardInterrupt:
            pass

#ana menü fonksiyonu
def main_menu():
    while True:
        console.print("\n", Panel.fit(
            "[bold cyan]1.[/bold cyan] Tekli Dosya Analizi (Örn: /var/log/test.log)\n"
            "[bold cyan]2.[/bold cyan] Toplu Dosya (Klasör) Analizi (Örn: /var/log)\n"
            "[bold cyan]3.[/bold cyan] Canlı (tail mod) İzleme (Örn: /var/log/test.log)\n"
            "[bold cyan]4.[/bold cyan] Çıkış",
            title="🛡️ LOG ANALIZ SISTEMI", border_style="blue"
        ))
        choice = console.input("[bold yellow]Seçiminiz: [/bold yellow]")
        if choice == "1": analyze_log(console.input("Dosya yolu: ", markup=False) or "/var/log/test.log")
        elif choice == "2": analyze_directory(console.input("Klasör yolu: ", markup=False) or "/var/log")
        elif choice == "3": tail_log(console.input("İzlenecek dosya: ", markup=False) or "/var/log/test.log")
        elif choice == "4": break

if __name__ == "__main__":
    main_menu()