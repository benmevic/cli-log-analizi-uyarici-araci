# Python daha hafif bir versiyonu
FROM python:3.11-slim

WORKDIR /app

# Kütüphane listesi konteyner içine kopyalanıyor.
COPY requirements.txt .

# Gerekli kütüphanelerin kurulumu.
RUN pip install --no-cache-dir -r requirements.txt

# Tüm kodlar ve kural dosyası kopyalanıyor.
COPY main.py .
COPY rules.json .

# Çıktıların kaydedileceği klasör oluşturuluyor.
RUN mkdir -p outputs

# Program başlangıcı
CMD ["python3", "main.py"]