import requests
from bs4 import BeautifulSoup
import csv
import datetime
import re
import xml.dom.minidom as md
from xml.etree.ElementTree import Element, SubElement, tostring
import html
import logging
import time

def scrape_ytu_events():
    """YTÜ etkinlik sayfasından etkinlikleri çeker"""
    # URL of the YTU events page
    url = 'https://www.yildiz.edu.tr/universite/haberler/ytu-etkinlik-takvimi'
    
    # Send a GET request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        logging.basicConfig(level=logging.INFO, filename='scrape_log.txt', filemode='a')
        for attempt in range(3):  # Retry up to 3 times
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                logging.info(f"Request to {url} returned status code: {response.status_code}")
                if response.status_code != 200:
                    logging.error(f"Failed to fetch page: Status code {response.status_code}")
                break  # Success, exit loop
            except requests.exceptions.RequestException as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < 2:  # Wait before next attempt
                    time.sleep(5)  # Wait 5 seconds
        else:
            raise Exception("All attempts failed")
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # List to store event information
        events = []
        
        # Define month abbreviations in Turkish for date parsing
        month_abbr_map = {
            'Oca': '01', 'Şub': '02', 'Mar': '03', 'Nis': '04', 
            'May': '05', 'Haz': '06', 'Tem': '07', 'Ağu': '08', 
            'Eyl': '09', 'Eki': '10', 'Kas': '11', 'Ara': '12'
        }
        
        # Yeni site yapısına göre etkinlikleri çekelim
        # Etkinlik blokları a etiketleri içinde
        event_links = soup.find_all('a', href=lambda href: href and 'universite/ytu-etkinlik-takvimi/' in href)
        
        # Her bir etkinlik için
        processed_urls = set()  # İşlenen URL'leri takip etmek için
        
        for i in range(0, len(event_links), 2):  # İkişer ikişer atlayarak (tarih ve başlık linkleri)
            if i+1 >= len(event_links):
                continue
                
            # Tarih linki
            date_link = event_links[i]
            # Başlık linki
            title_link = event_links[i+1]
            
            # URL'i kontrol et (aynı etkinliğe birden fazla link olabilir)
            event_url = title_link['href']
            if event_url in processed_urls:
                continue
            processed_urls.add(event_url)
            
            # Tarih bilgisini çıkar (örn: 24May)
            date_text = date_link.get_text().strip()
            if not re.match(r'^\d{2}(Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)$', date_text):
                continue
                
            day = date_text[:2]
            month_abbr = date_text[2:]
            month = month_abbr_map.get(month_abbr, '01')
            
            # Başlık ve detayları çıkar
            title_block = title_link.get_text().strip()
            title_parts = title_block.split('Yer :')
            
            title = title_parts[0].strip()
            location = ''
            
            if len(title_parts) > 1:
                location_time_parts = title_parts[1].split('Saat :')
                if len(location_time_parts) > 0:
                    location = location_time_parts[0].strip()
            
            # Saat bilgisini çıkar
            time_match = re.search(r'Saat\s*:\s*(\d{1,2}:\d{2})', title_block)
            time = time_match.group(1) if time_match else ''
            
            # Tarih oluştur
            current_year = datetime.datetime.now().year
            date_str = f"{day}/{month}/{current_year}"
            
            # URL düzenle
            clean_url = event_url
            if not clean_url.startswith('http'):
                clean_url = 'https://www.yildiz.edu.tr' + clean_url
            
            # Event objesi oluştur
            event = {
                'title': title,
                'url': clean_url,
                'date': date_str,
                'time': time,
                'location': location,
                'description': '',
                'day_month': f"{day}{month_abbr}"
            }
            
            # Açıklama oluştur
            description_parts = []
            if date_str:
                description_parts.append(f"Tarih: {date_str}")
            if time:
                description_parts.append(f"Saat: {time}")
            if location:
                description_parts.append(f"Yer: {location}")
            
            event['combined_description'] = "\n".join(description_parts)
            
            # Etkinlikler listesine ekle
            events.append(event)
        
        # Tekrarlayan etkinlikleri kaldır (aynı başlık ve saat)
        unique_events = []
        seen = set()
        
        for event in events:
            # Başlık ve saate göre anahtar oluştur
            key = (event['title'], event['time'])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        logging.info(f"Number of unique events after filtering: {len(unique_events)}")
        if not unique_events:
            logging.warning("No unique events were found after filtering.")
            
        return unique_events
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return []

def generate_rss(events, filename):
    """Etkinliklerden RSS dosyası oluşturur"""
    # Create the root element
    rss = Element('rss', {'version': '2.0'})
    
    # Create channel element
    channel = SubElement(rss, 'channel')
    
    # Add channel information
    title = SubElement(channel, 'title')
    title.text = 'YTU Etkinlik Takvimi'
    
    link = SubElement(channel, 'link')
    link.text = 'https://www.yildiz.edu.tr/universite/haberler/ytu-etkinlik-takvimi'
    
    description = SubElement(channel, 'description')
    description.text = 'Yıldız Teknik Üniversitesi Etkinlik Takvimi'
    
    language = SubElement(channel, 'language')
    language.text = 'tr-TR'
    
    lastBuildDate = SubElement(channel, 'lastBuildDate')
    lastBuildDate.text = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0300')
    
    # Add items (events)
    for event in events:
        item = SubElement(channel, 'item')
        
        item_title = SubElement(item, 'title')
        item_title.text = event['title']
        
        item_link = SubElement(item, 'link')
        item_link.text = event['url']
        
        item_description = SubElement(item, 'description')
        item_description.text = event.get('combined_description', '')
        
        # Add a GUID (use the URL as the GUID)
        item_guid = SubElement(item, 'guid')
        item_guid.text = event['url']
        
        # Try to parse the date if possible
        pubDate = SubElement(item, 'pubDate')
        try:
            # Try to parse the date if it's in a recognizable format
            date_str = event.get('date', '')
            if date_str and date_str != 'Date not found':
                # Try different date formats
                try:
                    # Format: DD/MM/YYYY
                    date_parts = date_str.split('/')
                    if len(date_parts) == 3:
                        day, month, year = date_parts
                        event_date = datetime.datetime(int(year), int(month), int(day))
                        pubDate.text = event_date.strftime('%a, %d %b %Y %H:%M:%S +0300')
                except:
                    # Default to current date if parsing fails
                    pubDate.text = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0300')
            else:
                # Default to current date if no date is available
                pubDate.text = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0300')
        except:
            # Default to current date if parsing fails
            pubDate.text = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0300')
    
    # Convert to XML string with proper formatting
    rough_string = tostring(rss, 'utf-8')
    reparsed = md.parseString(rough_string)
    
    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(reparsed.toprettyxml(indent="  "))
    
    print(f"RSS feed successfully generated: {filename}")

if __name__ == "__main__":
    # Scrape events from the website
    print("YTÜ etkinliklerini çekiyor...")
    events = scrape_ytu_events()
    
    if events:
        print(f"{len(events)} etkinlik bulundu")
        # Generate RSS file
        generate_rss(events, "ytu_etkinlikler.xml")
        
        # Print the first 5 events as a sample
        print("\n" + "=" * 60)
        print("OLUŞTURULAN ETKİNLİKLER ÖRNEĞİ")
        print("=" * 60)
        
        # En fazla 5 etkinlik göster
        sample_events = events[:min(5, len(events))]
        
        for i, event in enumerate(sample_events, 1):
            print(f"\nEtkinlik {i}:")
            print(f"Başlık: {event['title']}")
            # URL'yi kısalt ve sadece son kısmını göster
            url_parts = event['url'].split('/')
            short_url = url_parts[-1] if len(url_parts) > 0 else event['url']
            print(f"URL kısmı: {short_url}")
            print(f"Tarih: {event.get('date', '')}")
            print(f"Saat: {event.get('time', '')}")
            print(f"Yer: {event.get('location', '')}")
            print("-" * 60)
        
        print(f"\nToplam {len(events)} etkinlik bulundu ve RSS beslemesi oluşturuldu.")
        print(f"RSS dosyası: ytu_etkinlikler.xml")
    else:
        logging.error("Hiç etkinlik bulunamadı. RSS beslemesi oluşturulamadı.")
        print("Hiç etkinlik bulunamadı. RSS beslemesi oluşturulamadı.")