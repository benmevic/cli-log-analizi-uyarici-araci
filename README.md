# CLI Log Analizi ve Uyarici Araci

Terminal tabanli, kural destekli log analiz aracidir. Tek bir log dosyasini analiz edebilir, CSV rapor uretebilir ve `plugins/` klasorundeki eklentileri otomatik yukleyerek menuyu genisletebilir.

Bu surumde ana uygulamaya plugin mimarisi ve `Gercek Zamanli Veri Isleme` plugini eklendi. Plugin buyuk log dosyalarini RAM'e almadan satir satir isler, kategori/kelime filtresi uygular, eslesen olaylari canli panelde gosterir ve CSV olarak `outputs/` klasorune yazar.

## Ozellikler

- `rules.json` uzerinden keyword, kategori ve etiket bazli log eslestirme
- Tekli dosya analizi ve kategori bazli ozet tablo
- CSV rapor ciktilari (`outputs/rapor_<tarih>.csv`)
- Otomatik plugin kesfi (`plugins/*.py`)
- Buyuk loglar icin streaming dosya tarama modu
- Dosya sonundan canli izleme modu
- Kategori filtresi (`KRITIK,HATA` gibi)
- Ek kelime filtresi
- Rich destekli terminal tablo/panel arayuzu
- Docker ile tasinabilir calisma ortami

## Proje Yapisi

```text
.
|-- main.py
|-- rules.json
|-- requirements.txt
|-- Dockerfile
|-- .dockerignore
|-- plugins/
|   `-- live_tail.py
|-- logs/
|   |-- buyuk_karma_akis.log
|   |-- log1.txt
|   |-- ssh_auth.log
|   |-- system.log
|   `-- web_access.log
|-- screenshots/
|   |-- bulk_analysis.png
|   |-- live_tail.png
|   `-- menu.png
`-- outputs/
```

`outputs/` klasoru calisma sirasinda uretilen CSV raporlari icindir. `.gitignore` bu rapor dosyalarini repoya eklemez.

## Yerel Python ile Calistirma

Gereksinimler:

- Python 3.11+
- pip

Kurulum:

```bash
pip install -r requirements.txt
```

Calistirma:

```bash
python main.py
```

Varsayilan menu:

```text
1. Tekli Dosya Analizi
2. Gercek zamanli veri isleme - buyuk log akisini satir satir parse eder
3. Cikis
```

## Docker ile Calistirma

Image olusturma:

```bash
docker build -t log-analiz-cli .
```

Container calistirma:

```bash
docker run -it --rm log-analiz-cli
```

CSV raporlarini bilgisayardaki `outputs/` klasorune yazdirmak icin:

PowerShell:

```powershell
docker run -it --rm -v "${PWD}/outputs:/app/outputs" log-analiz-cli
```

Linux/macOS:

```bash
docker run -it --rm -v "$(pwd)/outputs:/app/outputs" log-analiz-cli
```

## Tekli Dosya Analizi

Menuden `1` secilir ve analiz edilecek log dosyasi girilir:

```text
Seciminiz: 1
Dosya yolu: logs/log1.txt
```

Uygulama `rules.json` icindeki kurallara gore eslesen satirlari bulur, ekranda kategori ozetini gosterir ve CSV rapora yazar.

## Gercek Zamanli Veri Isleme Plugini

Menuden plugin secildiginde iki mod vardir:

```text
Seciminiz: 2
Izlenecek/islenecek dosya: logs/buyuk_karma_akis.log
Mod secin [1=mevcut dosyayi stream tara, 2=sondan canli izle] (varsayilan 2): 1
Kategori filtresi (bos=hepsi, ornek: KRITIK,HATA): KRITIK,HATA
Ek kelime filtresi (bos=hepsi):
```

Modlar:

- `1`: Mevcut dosyayi bastan sona streaming olarak tarar.
- `2`: Dosyanin sonuna gider ve yeni eklenen satirlari canli izler.

Canli izleme modunu durdurmak icin `CTRL+C` kullanilir.

## Plugin Mimarisi

Uygulama acilisinda `plugins/` klasorundeki Python dosyalarini tarar. Bir dosyanin plugin olarak menuye eklenmesi icin su alanlari saglamasi gerekir:

```python
PLUGIN_NAME = "Plugin Adi"
PLUGIN_DESC = "Menude gorunecek aciklama"

def run(console, load_rules, save_to_csv):
    ...
```

`run(...)` fonksiyonu ana uygulamadan su yardimcilari alir:

- `console`: Rich console nesnesi
- `load_rules`: `rules.json` kurallarini okuyan fonksiyon
- `save_to_csv`: standart CSV raporuna satir ekleyen fonksiyon

Bu yapi sayesinde ana menuyu degistirmeden yeni analiz modlari eklenebilir.

## Kural Dosyasi

Kurallar `rules.json` icinde tutulur:

```json
{
  "keyword": "failed password",
  "kategori": "GUVENLIK",
  "label": "SSH basarisiz giris"
}
```

Desteklenen varsayilan kategoriler:

- `KRITIK`
- `HATA`
- `BILGI`
- `GUVENLIK`

## Ornek Loglar

Repoda test icin hazir log dosyalari bulunur:

| Dosya | Aciklama |
| --- | --- |
| `logs/log1.txt` | Temel tekli analiz ornegi |
| `logs/web_access.log` | Web erisim ve hata loglari |
| `logs/ssh_auth.log` | SSH giris denemeleri |
| `logs/system.log` | Sistem ve servis loglari |
| `logs/buyuk_karma_akis.log` | Streaming/canli analiz icin karma log akisi |

## RAM'e Almadan Isleme Mantigi

Plugin buyuk dosyalari `read()` veya `readlines()` ile bellekte toplamaz. Streaming modda dosya satir satir okunur:

```python
for line in handle:
    process_line(line)
```

Canli izleme modunda dosyanin sonuna gidilir ve sadece yeni satirlar takip edilir:

```python
handle.seek(0, os.SEEK_END)
line = handle.readline()
```

Ekranda yalnizca son 15 eslesme tutulur:

```python
recent_events = deque(maxlen=DISPLAY_LIMIT)
```

Bu nedenle log dosyasi buyuse bile uygulama tum icerigi RAM'e yuklemeden calisir.
