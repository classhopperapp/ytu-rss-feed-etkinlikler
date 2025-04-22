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
        
        # From the error pattern, it looks like we need to be more specific
        # Let's try to find the actual event containers
        
        # Method 1: Look for main content area and find event items
        content_area = soup.select_one('.main-content, #content, .content, main')
        
        if content_area:
            # Look for individual event items within the content area
            event_items = content_area.select('.event-item, .calendar-item, .news-item, article, .card, .box')
            
            if not event_items:
                # If no specific event items found, look for list items or divs that might contain events
                event_items = content_area.select('li, .row > div, .col > div')
        else:
            # If no content area identified, search throughout the page
            event_items = soup.select('.event-item, .calendar-item, .news-item, article, .card, .box')
        
        # Process found items
        for item in event_items:
            # Ignore items that are clearly navigation or filters
            item_text = item.get_text(strip=True).lower()
            
            # Skip items that look like navigation
            if any(nav_term in item_text for nav_term in ['yil', 'ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 
                                                          'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık', 'tümü']):
                continue
                
            # Skip very short or empty items
            if len(item_text) < 10:
                continue
                
            # Extract title - look for headings first
            title_element = item.select_one('h1, h2, h3, h4, h5, .title, .heading, strong')
            
            if title_element:
                title = title_element.get_text(strip=True)
            else:
                # If no heading found, use the first substantial text
                paragraphs = item.select('p')
                if paragraphs:
                    title = paragraphs[0].get_text(strip=True)
                else:
                    # Last resort, just use the text
                    title = item.get_text(strip=True)[:100]  # Limit length
            
            # Remove any excessive whitespace and newlines
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Extract URL
            link = item.select_one('a')
            event_url = ""
            if link and link.has_attr('href'):
                event_url = link['href']
                # Handle relative URLs
                if event_url.startswith('/'):
                    event_url = 'https://www.yildiz.edu.tr' + event_url
            
            # Extract date
            # Look for common date formats in the text
            date_element = item.select_one('.date, .datetime, time, .calendar-date')
            event_date = "Date not found"
            
            if date_element:
                event_date = date_element.get_text(strip=True)
            else:
                # Try to find date patterns
                text = item.get_text()
                date_patterns = [
                    r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
                    r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
                    r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
                    r'\d{1,2} \w+ \d{4}'         # DD Month YYYY
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, text)
                    if match:
                        event_date = match.group(0)
                        break
            
            # Extract description if available
            description = ""
            desc_element = item.select_one('p.description, .desc, .summary, .content')
            if desc_element:
                description = desc_element.get_text(strip=True)
            else:
                # Try to find a paragraph that might contain a description
                paragraphs = item.select('p')
                if len(paragraphs) > 1:  # Skip first paragraph if it might be title
                    description = paragraphs[1].get_text(strip=True)
            
            # Filter out incomplete or invalid entries
            if title and not title.startswith('YIL') and not title.startswith('AY'):
                events.append({
                    'title': title,
                    'url': event_url,
                    'date': event_date,
                    'description': description
                })
        
        # Alternative method: Try to find a specific event listing pattern
        if not events:
            # Check for event listings that might be in a specific format
            all_links = soup.select('a')
            event_links = []
            
            for link in all_links:
                href = link.get('href', '')
                
                # Look for links that might be event details
                if 'etkinlik' in href or 'event' in href or 'haber' in href or 'news' in href:
                    # Check if this link has not been processed yet
                    if not any(e['url'] == href for e in events):
                        title = link.get_text(strip=True)
                        
                        # Skip navigation links and very short titles
                        if (title and len(title) > 10 and 
                            not any(nav_term in title.lower() for nav_term in 
                                   ['yil', 'ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 
                                    'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık', 'tümü'])):
                            
                            # Look for a date near this link
                            parent = link.parent
                            siblings = list(parent.parent.children)
                            
                            event_date = "Date not found"
                            description = ""
                            
                            for sibling in siblings:
                                if hasattr(sibling, 'get_text'):
                                    text = sibling.get_text(strip=True)
                                    # Check for date patterns
                                    date_patterns = [
                                        r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
                                        r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
                                        r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
                                        r'\d{1,2} \w+ \d{4}'         # DD Month YYYY
                                    ]
                                    
                                    for pattern in date_patterns:
                                        match = re.search(pattern, text)
                                        if match:
                                            event_date = match.group(0)
                                            break
                                    
                                    # If this isn't a date and isn't the title, it might be a description
                                    if (event_date == "Date not found" and 
                                        text != title and 
                                        len(text) > 20):
                                        description = text
                            
                            # Add to events
                            event_url = href
                            if event_url.startswith('/'):
                                event_url = 'https://www.yildiz.edu.tr' + event_url
                                
                            events.append({
                                'title': title,
                                'url': event_url,
                                'date': event_date,
                                'description': description
                            })
            
        return events
            
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
        item_link.text = event['url']
        
        item_desc = SubElement(item, 'description')
        
        # Create a more detailed description using both date and description
        desc_text = f"Tarih: {event['date']}"
        if event['description']:
            desc_text += f"\n\n{event['description']}"
        
        item_desc.text = desc_text
        
        item_guid = SubElement(item, 'guid')
        item_guid.text = event['url']
        
        # Try to parse the date if possible
        pubDate = SubElement(item, 'pubDate')
        try:
            # Try to parse the date if it's in a recognizable format
            # This is a simplistic approach and might need adjustment
            date_str = event['date']
            if date_str != "Date not found":
                # Try different date formats
                date_formats = [
                    '%d.%m.%Y',  # DD.MM.YYYY
                    '%d/%m/%Y',  # DD/MM/YYYY
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

if __name__ == "__main__":
    # Scrape events
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
            print(f"Date: {event['date']}")
            if event.get('description'):
                print(f"Description: {event['description']}")
            print("-" * 50)
    else:
        print("No events found. Cannot generate RSS feed.")