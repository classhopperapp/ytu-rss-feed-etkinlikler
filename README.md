# YTÜ Etkinlik Takvimi RSS Üreteci

Bu proje, Yıldız Teknik Üniversitesi'nin etkinlik takvimi sayfasından etkinlikleri çekip RSS beslemesi oluşturan bir araçtır.

## Özellikler

- YTÜ etkinlik takvimi sayfasından etkinlikleri otomatik olarak çeker
- Etkinliklerin başlık, tarih, saat ve yer bilgilerini ayıklar
- Tekrarlayan etkinlikleri filtreler
- Standart RSS 2.0 formatında besleme oluşturur
- Türkçe karakter desteği

## Kullanım

Programı çalıştırmak için:

```bash
python rss_generator.py
```

Bu komut, etkinlikleri çekip `ytu_etkinlikler.xml` dosyasına kaydeder.

## Teknik Detaylar

### Bağımlılıklar

- Python 3.6+
- requests
- beautifulsoup4
- xml.etree.ElementTree (Python standart kütüphanesi)
- xml.dom.minidom (Python standart kütüphanesi)

Gerekli kütüphaneleri yüklemek için:

```bash
pip install -r requirements.txt
```

### Kod Yapısı

- `scrape_ytu_events()`: YTÜ etkinlik sayfasından etkinlikleri çeker
- `generate_rss(events, filename)`: Etkinliklerden RSS dosyası oluşturur

## Son Değişiklikler

### 1 Mayıs 2025

- Kod tamamen güncel YTÜ web sitesi yapısına göre yeniden yazıldı
- HTML yapısını analiz ederek etkinlikleri çekme mantığı değiştirildi
- Etkinlik linklerini ve tarih bilgilerini doğru şekilde ayıklama eklendi
- Yer ve saat bilgilerini HTML yapısından çıkarma mantığı güncellendi
- Tüm çıktılar Türkçeleştirildi
- Konsol çıktısı formatı iyileştirildi
- URL'ler kısaltılarak konsol çıktısındaki karışıklık önlendi
- Kod içine açıklama satırları eklendi

## Notlar

- RSS beslemesi, etkinliklerin tarih, saat ve yer bilgilerini içerir
- Etkinlik URL'leri YTÜ'nün resmi etkinlik sayfasına yönlendirilir
- Tarih formatı: GG/AA/YYYY
- Saat formatı: SS:DD
- RSS dosyası UTF-8 kodlaması ile kaydedilir

## Lisans

Bu proje açık kaynaklıdır ve MIT lisansı altında dağıtılmaktadır.
