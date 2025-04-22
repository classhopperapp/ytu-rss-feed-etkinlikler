import requests
from bs4 import BeautifulSoup
import csv
import datetime
import re
import xml.dom.minidom as md
from xml.etree.ElementTree import Element, SubElement, tostring
import html

def scrape_ytu_events():
    # URL of the YTU events page
    url = 'https://www.yildiz.edu.tr/universite/haberler/ytu-etkinlik-takvimi'
    
    # Send a GET request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # List to store event information
        events = []
        
        # Get the main content text
        content_text = soup.get_text()
        
        # Parse events from the raw text using regex patterns
        # This approach is more reliable for the specific YTU events page structure
        
        # Define month abbreviations in Turkish for date parsing
        month_abbr_map = {
            'Oca': '01', 'Şub': '02', 'Mar': '03', 'Nis': '04', 
            'May': '05', 'Haz': '06', 'Tem': '07', 'Ağu': '08', 
            'Eyl': '09', 'Eki': '10', 'Kas': '11', 'Ara': '12'
        }
        
        # Pattern to match event blocks: date code + title + location + time
        # Example: "16EylYTÜ Bilimsel Araştırma Projesi Hazırlama Eğitimi Başlıyor YTÜ Elektrik-Elektronik Fakültesi Konferans SalonuSaat : 09:00"
        event_pattern = r'(\d{2})(Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)([^S]+)Saat\s*:\s*(\d{1,2}:\d{2})'
        
        # Find all matches
        event_matches = re.finditer(event_pattern, content_text)
        
        for match in event_matches:
            day = match.group(1)
            month_abbr = match.group(2)
            month = month_abbr_map.get(month_abbr, '01')  # Default to January if not found
            title_and_location = match.group(3).strip()
            time = match.group(4)
            
            # Try to separate title and location
            # Location often follows the title and may contain specific venue information
            location = ""
            title = title_and_location
            
            # Check if there's a location part (usually contains campus names, building names, etc.)
            location_indicators = [
                "Kampüsü", "Fakültesi", "Salonu", "Merkezi", "Müzesi", 
                "Konferans", "Çevrim İçi", "YTÜ", "Davutpaşa", "Oditoryum",
                "İstanbul Modern"
            ]
            
            # Remove "Yer :" from the title if present
            if "Yer :" in title:
                title = title.split("Yer :")[0].strip()
            
            # Try to find where the location starts
            location_parts = []
            for indicator in location_indicators:
                if indicator in title_and_location:
                    # Find the last occurrence of the indicator
                    pos = title_and_location.rfind(indicator)
                    if pos > len(title_and_location) // 3:  # Only consider if it's in the latter part of the string
                        # Look for the start of the location phrase
                        start_pos = max(0, title_and_location[:pos].rfind(" "))
                        location_part = title_and_location[start_pos:].strip()
                        location_parts.append(location_part)
                        
            if location_parts:
                # Use the longest location part found
                location = max(location_parts, key=len)
                # Remove the location from the title
                title = title_and_location.replace(location, "").strip()
            
            # If no location was found, check if "Yer :" appears in the text after this match
            if not location:
                next_text = content_text[match.end():match.end() + 100]
                yer_match = re.search(r'Yer\s*:\s*([^\n]+)', next_text)
                if yer_match:
                    location = yer_match.group(1).strip()
            
            # Create a date string (use current year as we don't have year in the data)
            current_year = datetime.datetime.now().year
            date_str = f"{day}/{month}/{current_year}"
            
            # Create URL for the event
            # Convert title to URL-friendly format
            url_title = title.lower().replace(" ", "-").replace(":", "").replace("?", "").replace(".", "")
            url_title = re.sub(r'[^a-z0-9-]', '', url_title.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c'))
            event_url = f"https://www.yildiz.edu.tr/universite/ytu-etkinlik-takvimi/{url_title}"
            
            # Create event object
            event = {
                'title': title,
                'url': event_url,
                'date': date_str,
                'time': time,
                'location': location,
                'description': '',
                'day_month': f"{day}{month_abbr}"  # Store the original day+month code
            }
            
            # Create a combined description
            description_parts = []
            if date_str:
                description_parts.append(f"Tarih: {date_str}")
            if time:
                description_parts.append(f"Saat: {time}")
            if location:
                description_parts.append(f"Yer: {location}")
            
            event['combined_description'] = "\n".join(description_parts)
            
            # Add to events list
            events.append(event)
        
        # Remove duplicate events (same title and time)
        unique_events = []
        seen = set()
        
        for event in events:
            # Create a key based on title and time
            key = (event['title'], event['time'])
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
        
        return unique_events
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def generate_rss(events, filename):
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
        item_link.text = event['url'] if event['url'] else 'https://www.yildiz.edu.tr/universite/haberler/ytu-etkinlik-takvimi'
        
        item_desc = SubElement(item, 'description')
        item_desc.text = event.get('combined_description', '')
        
        item_guid = SubElement(item, 'guid')
        if event['url']:
            item_guid.text = event['url']
        else:
            # Generate a unique ID using title and other info
            guid_components = [event['title']]
            if event.get('date'):
                guid_components.append(event['date'])
            if event.get('time'):
                guid_components.append(event['time'])
            guid = '-'.join(guid_components).replace(' ', '-')
            item_guid.text = f"https://www.yildiz.edu.tr/event/{guid}"
        
        # Try to parse the date if possible
        pubDate = SubElement(item, 'pubDate')
        try:
            # Try to parse the date if it's in a recognizable format
            date_str = event.get('date', '')
            if date_str and date_str != 'Date not found':
                # Try different date formats
                date_formats = [
                    '%d/%m/%Y',  # DD/MM/YYYY
                    '%d.%m.%Y',  # DD.MM.YYYY
                    '%Y-%m-%d',  # YYYY-MM-DD
                ]
                
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if parsed_date:
                    pubDate.text = parsed_date.strftime('%a, %d %b %Y %H:%M:%S +0300')
                else:
                    pubDate.text = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0300')
            else:
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

def parse_raw_data(raw_data):
    """Parse raw data directly provided by the user"""
    events = []
    
    # Define month abbreviations in Turkish for date parsing
    month_abbr_map = {
        'Oca': '01', 'Şub': '02', 'Mar': '03', 'Nis': '04', 
        'May': '05', 'Haz': '06', 'Tem': '07', 'Ağu': '08', 
        'Eyl': '09', 'Eki': '10', 'Kas': '11', 'Ara': '12'
    }
    
    # Pattern to match event entries
    # Example: "24MayYaratıcı Drama Atölyesi: Yıldızlı Olmak YTÜ MüzesiSaat : 12:00"
    event_pattern = r'(\d{2})(Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)([^S]+)Saat\s*:\s*(\d{1,2}:\d{2})'
    
    # Find all matches
    event_matches = re.finditer(event_pattern, raw_data)
    
    for match in event_matches:
        day = match.group(1)
        month_abbr = match.group(2)
        month = month_abbr_map.get(month_abbr, '01')  # Default to January if not found
        title_and_location = match.group(3).strip()
        time = match.group(4)
        
        # Split title and location
        title = title_and_location
        location = ""
        
        # Check if location is specified with "Yer :" prefix
        if "Yer :" in title_and_location:
            parts = title_and_location.split("Yer :")
            title = parts[0].strip()
            if len(parts) > 1:
                location = parts[1].strip()
        else:
            # Try to identify location based on common venue indicators
            location_indicators = [
                "Kampüsü", "Fakültesi", "Salonu", "Merkezi", "Müzesi", 
                "Konferans", "Çevrim İçi", "YTÜ", "Davutpaşa", "Oditoryum",
                "İstanbul Modern"
            ]
            
            # Find the longest matching location
            best_match = None
            best_match_len = 0
            
            for indicator in location_indicators:
                if indicator in title_and_location:
                    # Find all occurrences of the indicator
                    for match_obj in re.finditer(indicator, title_and_location):
                        pos = match_obj.start()
                        # Find the beginning of the location phrase
                        start_pos = max(0, title_and_location[:pos].rfind(" "))
                        if start_pos > 0:
                            # Get the location phrase
                            loc_phrase = title_and_location[start_pos:].strip()
                            if len(loc_phrase) > best_match_len:
                                best_match = loc_phrase
                                best_match_len = len(loc_phrase)
            
            if best_match:
                location = best_match
                # Remove the location from the title
                title = title_and_location[:title_and_location.rfind(best_match)].strip()
            else:
                title = title_and_location
        
        # Create a date string
        current_year = datetime.datetime.now().year
        date_str = f"{day}/{month}/{current_year}"
        
        # Create URL for the event
        url_title = title.lower().replace(" ", "-").replace(":", "").replace("?", "").replace(".", "")
        url_title = re.sub(r'[^a-z0-9-]', '', url_title.replace('ş', 's').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ö', 'o').replace('ç', 'c'))
        event_url = f"https://www.yildiz.edu.tr/universite/ytu-etkinlik-takvimi/{url_title}"
        
        # Create event object
        event = {
            'title': title,
            'url': event_url,
            'date': date_str,
            'time': time,
            'location': location,
            'description': '',
            'day_month': f"{day}{month_abbr}"  # Store the original day+month code
        }
        
        # Create combined description
        description_parts = []
        if date_str:
            description_parts.append(f"Tarih: {date_str}")
        if time:
            description_parts.append(f"Saat: {time}")
        if location:
            description_parts.append(f"Yer: {location}")
        
        event['combined_description'] = "\n".join(description_parts)
        
        # Add to events list
        events.append(event)
    
    # Remove duplicate events (same title and time)
    unique_events = []
    seen = set()
    
    for event in events:
        # Create a key based on title and time
        key = (event['title'], event['time'])
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    
    return unique_events

if __name__ == "__main__":
    # Check if we have raw data provided by the user
    raw_data = """
    Yer: YIL2024202320222021AYOcakŞubatMartNisanMayısHaziranTemmuzAğustosEylülEkimKasımAralıkTÜMÜ02AraGörevde Yükselme ve Unvan Değişikliği Merkezi Yazılı Sınav SonuçlarıSaat : 13:4316EylYTÜ Bilimsel Araştırma Projesi Hazırlama Eğitimi Başlıyor YTÜ Elektrik-Elektronik Fakültesi Konferans SalonuSaat : 09:0007Hazİstanbul Modern Sanat Müzesi-YTÜ Haziran EğitimleriSaat : 13:0124MayYaratıcı Drama Atölyesi: Yıldızlı Olmak YTÜ MüzesiSaat : 12:0029MayGrad Talks: Additive Homeopathy Improves Quality of Life and Prolongs Survival in Patients with NSCLC Çevrim İçiSaat : 17:0017Mayİstanbul Modern Sanat Müzesi-YTÜ Mayıs Eğitimleri İstanbul Modern Sanat MüzesiSaat : 10:1004HazGradColloquium 2024 - Yapay Zeka Davupaşa Kampüsü-Tarihi HamamSaat : 09:0015MayPanel: Azerbaycan'da Eğitimin Gelişme Aşamaları, Türk Eğitimiyle İlişkiler Prof. Dr. Ahmet KARADENİZ Konferans Salonu - Fen-Edebiyat FakültesiSaat : 11:0017NisGrad Talks: Designing for Empathy: Why is it Essential for Our World?Saat : 21:0016Nisİstanbul Modern Sanat Müzesi-YTÜ Nisan EğitimleriSaat : 14:2111Marİstanbul Modern Sanat Müzesi-YTÜ Mart EğitimleriSaat : 16:4616Şubİstanbul Modern Sanat Müzesi-YTÜ Şubat EğitimleriSaat : 10:0121ŞubGrad Talks: Chalcogenide Glasses and Ceramics for IR Applications and Beyond Çevrim İçiSaat : 17:0031OcaRevolutionizing Climate Solutions: Unveiling the Energy and Economic Aspects of Direct Air Carbon Capture Çevrim İçiSaat : 17:0020ŞubCERN Masterclass Etkinliğini YTÜ'de düzenliyor. Davutpaşa KampüsüSaat : 10:0018OcaCanis Majoris 2023 Konseri Davutpaşa Kongre ve Kültür MerkeziSaat : 19:0017OcaTechnology Management Days in İstanbul Symposium YTÜ Yıldız Kampüsü- OditoryumSaat : 10:0027AraFBE Grad Careers Seminer Serisi 1 – Yıldızlı Akademisyenlerin Doktora Sonrası Uluslararası Kariyer Yolculukları Çevrim İçiSaat : 17:0021Ara10. Yıldız Uluslararası Sosyal Bilimler Kongresi Çevrim İçiSaat : 09:3019AraInternational Conference: At the Crossroads: Türkiye-India Relations Davutpaşa Kampüsü-İktisadi ve İdari Bilimler FakültesiSaat : 09:00SayfalamaPage1Page2Page3Page4Sonraki sayfa›Son sayfa»GeriPaylaş
    """
    
    if raw_data.strip():
        print("Parsing provided raw data...")
        events = parse_raw_data(raw_data)
    else:
        # Scrape events from the website
        print("Scraping YTU events...")
        events = scrape_ytu_events()
    
    if events:
        print(f"Found {len(events)} events")
        # Generate RSS file
        generate_rss(events, "ytu_etkinlikler.xml")
        
        # Print the first 5 events as a sample
        for i, event in enumerate(events[:5], 1):
            print(f"Event {i}:")
            print(f"Title: {event['title']}")
            print(f"URL: {event['url']}")
            print(f"Date: {event.get('date', '')}")
            print(f"Time: {event.get('time', '')}")
            print(f"Location: {event.get('location', '')}")
            if event.get('combined_description'):
                print(f"Description: {event['combined_description']}")
            print("-" * 50)
    else:
        print("No events found. Cannot generate RSS feed.")