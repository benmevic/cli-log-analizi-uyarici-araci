import os
import time
from collections import Counter, deque

from rich.console import Group
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

PLUGIN_NAME = "Gercek Zamanli Veri Isleme"
PLUGIN_DESC = "Gercek zamanli veri isleme - buyuk log akisini satir satir parse eder"

CATEGORIES = ("KRITIK", "HATA", "BILGI", "GUVENLIK")
DISPLAY_LIMIT = 15
SLEEP_SECONDS = 0.4


def normalize_category(value):
    return value.upper().strip()


def parse_category_filter(raw_filter):
    if not raw_filter:
        return set(), []

    selected = set()
    invalid = []
    for item in raw_filter.replace(";", ",").split(","):
        category = normalize_category(item)
        if not category:
            continue
        if category in CATEGORIES:
            selected.add(category)
        else:
            invalid.append(item.strip())

    return selected, invalid


def find_matching_rule(line, rules):
    lowered_line = line.lower()
    for rule in rules:
        keyword = str(rule.get("keyword", "")).lower()
        if keyword and keyword in lowered_line:
            return {
                "category": normalize_category(str(rule.get("kategori", "BILGI"))),
                "label": str(rule.get("label", keyword)),
            }
    return None


def line_passes_filters(line, match, category_filter, keyword_filter):
    if category_filter and match["category"] not in category_filter:
        return False
    if keyword_filter and keyword_filter not in line.lower():
        return False
    return True


def build_dashboard(file_path, mode_label, stats, processed, matched, filtered, unmatched, recent_events):
    stats_table = Table(title=f"{mode_label}: {file_path}")
    stats_table.add_column("Metrik", style="bold cyan")
    stats_table.add_column("Deger", justify="right", style="magenta")
    stats_table.add_row("Islenen satir", str(processed))
    stats_table.add_row("Eslesen ve kaydedilen", str(matched))
    stats_table.add_row("Filtreye takilan", str(filtered))
    stats_table.add_row("Kurala uymayan", str(unmatched))
    stats_table.add_section()

    for category in CATEGORIES:
        stats_table.add_row(category, str(stats.get(category, 0)))

    event_text = "\n".join(recent_events) if recent_events else "Henuz eslesen satir yok."
    return Group(
        stats_table,
        Panel(event_text, title="Son eslesmeler", border_style="blue"),
    )


def run(console, load_rules, save_to_csv):
    file_path = console.input("Izlenecek/islenecek dosya: ", markup=False).strip() or "logs/log1.txt"
    if not os.path.exists(file_path):
        console.print(f"[bold red]Hata:[/bold red] '{file_path}' bulunamadi!")
        return

    rules = load_rules()
    if not rules:
        console.print("[bold red]Hata:[/bold red] rules.json icinde aktif kural bulunamadi.")
        return

    mode = console.input(
        "Mod secin [1=mevcut dosyayi stream tara, 2=sondan canli izle] (varsayilan 2): ",
        markup=False,
    ).strip() or "2"
    watch_mode = mode != "1"

    raw_category_filter = console.input(
        "Kategori filtresi (bos=hepsi, ornek: KRITIK,HATA): ",
        markup=False,
    ).strip()
    category_filter, invalid_categories = parse_category_filter(raw_category_filter)
    if invalid_categories:
        console.print(
            "[yellow]Gecersiz kategori filtresi yok sayildi:[/yellow] "
            + ", ".join(invalid_categories)
        )

    keyword_filter = console.input(
        "Ek kelime filtresi (bos=hepsi): ",
        markup=False,
    ).strip().lower()

    stats = Counter()
    recent_events = deque(maxlen=DISPLAY_LIMIT)
    processed = 0
    matched = 0
    filtered = 0
    unmatched = 0

    def process_line(line):
        nonlocal processed, matched, filtered, unmatched

        processed += 1
        clean_line = line.strip()
        match = find_matching_rule(clean_line, rules)
        if match is None:
            unmatched += 1
            return

        if not line_passes_filters(clean_line, match, category_filter, keyword_filter):
            filtered += 1
            return

        category = match["category"] if match["category"] in CATEGORIES else "BILGI"
        label = match["label"]
        matched += 1
        stats[category] += 1

        now = time.strftime("%Y-%m-%d %H:%M:%S")
        save_to_csv([now, category, label, file_path, clean_line])

        recent_events.append(
            f"[blue]{time.strftime('%H:%M:%S')}[/blue] "
            f"[bold]{category}[/bold] {escape(label)} - {escape(clean_line[:160])}"
        )

    mode_label = "Canli akis" if watch_mode else "Streaming dosya tarama"

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            if watch_mode:
                from rich.live import Live

                handle.seek(0, os.SEEK_END)
                console.print("[cyan]Canli izleme basladi. Cikmak icin CTRL+C kullanin.[/cyan]")
                with Live(
                    build_dashboard(
                        file_path,
                        mode_label,
                        stats,
                        processed,
                        matched,
                        filtered,
                        unmatched,
                        recent_events,
                    ),
                    refresh_per_second=4,
                    screen=True,
                ) as live:
                    while True:
                        line = handle.readline()
                        if not line:
                            time.sleep(SLEEP_SECONDS)
                            continue
                        process_line(line)
                        live.update(
                            build_dashboard(
                                file_path,
                                mode_label,
                                stats,
                                processed,
                                matched,
                                filtered,
                                unmatched,
                                recent_events,
                            )
                        )
            else:
                for line in handle:
                    process_line(line)

                console.print(
                    build_dashboard(
                        file_path,
                        mode_label,
                        stats,
                        processed,
                        matched,
                        filtered,
                        unmatched,
                        recent_events,
                    )
                )
                console.print(
                    "[green]Dosya RAM'e alinmadan satir satir islenerek tamamlandi.[/green]"
                )
    except KeyboardInterrupt:
        console.print("\n[yellow]Canli izleme durduruldu.[/yellow]")
        console.print(
            build_dashboard(
                file_path,
                mode_label,
                stats,
                processed,
                matched,
                filtered,
                unmatched,
                recent_events,
            )
        )
    except OSError as exc:
        console.print(f"[bold red]Dosya okuma hatasi:[/bold red] {exc}")
