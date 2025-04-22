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
        
        # Based on the results, we need to find complete event containers
        # Let's try a different approach by looking for specific event patterns
        
        # Look for event containers - typically divs or sections containing complete event info
        event_containers = soup.select('.event-container, .event-box, .card, article, section.event')
        
        if event_containers:
            for container in event_containers:
                event_info = {
                    'title': '',
                    'url': '',
                    'date': '',
                    'time': '',
                    'location': '',
                    'description': ''
                }
                
                # Extract event title
                title_elem = container.select_one('h2, h3, h4, .event-title, .title')
                if title_elem:
                    event_info['title'] = title_elem.get_text(strip=True)
                
                # Extract event URL
                link_elem = container.select_one('a')
                if link_elem and link_elem.has_attr('href'):
                    url = link_elem['href']
                    if url.startswith('/'):
                        url = 'https://www.yildiz.edu.tr' + url
                    event_info['url'] = url
                
                # Extract date, time, location
                # Look for specific patterns or classes
                date_elem = container.select_one('.date, .event-date')
                if date_elem:
                    event_info['date'] = date_elem.get_text(strip=True)
                
                time_elem = container.select_one('.time, .event-time')
                if time_elem:
                    event_info['time'] = time_elem.get_text(strip=True)
                
                location_elem = container.select_one('.location, .venue, .place')
                if location_elem:
                    event_info['location'] = location_elem.get_text(strip=True)
                
                # Extract description
                desc_elem = container.select_one('.description, .summary, .content')
                if desc_elem:
                    event_info['description'] = desc_elem.get_text(strip=True)
                
                # Add to events if we have at least a title
                if event_info['title']:
                    events.append(event_info)
        
        # If the above approach didn't work, try to find event blocks using more specific patterns
        if not events:
            # Look for event listing structure
            # Based on output, we might be seeing individual fields instead of complete events
            # Let's try to reconstruct events by grouping related elements
            
            # Try to find the main content area first
            content_area = soup.select_one('.main-content, #content, .content, main, #main')
            
            if content_area:
                # Look for divs that might contain event info
                time_elements = content_area.select('div:contains("Saat :")')
                location_elements = content_area.select('div:contains("Yer :")')
                title_elements = content_area.select('h2, h3, h4, .event-title')
                
                # If we found time/location elements but not title elements, the titles might be near these elements
                if (time_elements or location_elements) and not title_elements:
                    # Try to find event blocks and extract complete information
                    for element in time_elements + location_elements:
                        # Find the parent container that might hold the complete event
                        event_container = find_parent_container(element)
                        
                        if event_container:
                            event_info = extract_event_from_container(event_container)
                            if event_info['title'] or event_info['description']:
                                events.append(event_info)
            
            # If still no events, try to find all direct event links as a fallback
            if not events:
                event_links = soup.select('a[href*="etkinlik"], a[href*="event"]')
                
                for link in event_links:
                    url = link['href']
                    if url.startswith('/'):
                        url = 'https://www.yildiz.edu.tr' + url
                    
                    title = link.get_text(strip=True)
                    
                    # Skip navigation links
                    if any(nav_term in title.lower() for nav_term in 
                          ['yil', 'ocak', 'şubat', 'mart', 'nisan', 'mayıs', 'haziran', 
                           'temmuz', 'ağustos', 'eylül', 'ekim', 'kasım', 'aralık', 'tümü']):
                        continue
                    
                    # Try to find related info near the link
                    parent = link.parent
                    
                    date = find_date_near_element(parent)
                    time = find_time_near_element(parent)
                    location = find_location_near_element(parent)
                    
                    events.append({
                        'title': title,
                        'url': url,
                        'date': date,
                        'time': time,
                        'location': location,
                        'description': ''
                    })
        
        # Try a more general approach - look for potential event blocks
        if not events:
            # Parse specific structure based on the observed output
            # It seems events might be divided into individual elements with time, location, etc.
            
            # First, get all divs with "Saat :" text - these appear to be time indicators
            time_divs = soup.find_all(lambda tag: tag.name == 'div' and 'Saat :' in tag.text)
            location_divs = soup.find_all(lambda tag: tag.name == 'div' and 'Yer :' in tag.text)
            
            # Group these elements into event objects
            event_dict = {}
            
            # Process time divs
            for time_div in time_divs:
                # Get the text content and clean it
                time_text = time_div.get_text(strip=True).replace('Saat :', '').strip()
                
                # Try to find nearby elements that might be related
                parent = time_div.parent
                siblings = list(parent.find_all(recursive=False))
                
                # Generate a key for this event based on position
                key = f"event_{time_divs.index(time_div)}"
                
                # Create or update event entry
                if key not in event_dict:
                    event_dict[key] = {
                        'title': '',
                        'url': '',
                        'date': '',
                        'time': time_text,
                        'location': '',
                        'description': ''
                    }
                else:
                    event_dict[key]['time'] = time_text
                
                # Look for event title around this time element
                title_elem = find_title_near_element(time_div)
                if title_elem:
                    event_dict[key]['title'] = title_elem
                
                # Look for date around this time element
                date = find_date_near_element(time_div)
                if date:
                    event_dict[key]['date'] = date
            
            # Process location divs and match them to events
            for loc_div in location_divs:
                location_text = loc_div.get_text(strip=True).replace('Yer :', '').strip()
                
                # Try to find which event this location belongs to
                # Use the nearest time div as a reference
                nearest_time_div = None
                min_distance = float('inf')
                
                for time_div in time_divs:
                    # Calculate "distance" in the DOM tree
                    distance = dom_distance(time_div, loc_div)
                    if distance < min_distance:
                        min_distance = distance
                        nearest_time_div = time_div
                
                if nearest_time_div:
                    key = f"event_{time_divs.index(nearest_time_div)}"
                    if key in event_dict:
                        event_dict[key]['location'] = location_text
                    
                # If no matching time div found, this might be a separate event
                else:
                    key = f"event_loc_{location_divs.index(loc_div)}"
                    event_dict[key] = {
                        'title': '',
                        'url': '',
                        'date': '',
                        'time': '',
                        'location': location_text,
                        'description': ''
                    }
                    
                    # Look for event title around this location element
                    title_elem = find_title_near_element(loc_div)
                    if title_elem:
                        event_dict[key]['title'] = title_elem
            
            # Convert dictionary to list of events
            for key, event_info in event_dict.items():
                # If we don't have a title yet, try to construct one from time and location
                if not event_info['title']:
                    components = []
                    if event_info['time']:
                        components.append(f"Etkinlik - {event_info['time']}")
                    if event_info['location']:
                        components.append(f"at {event_info['location']}")
                    
                    if components:
                        event_info['title'] = " ".join(components)
                    else:
                        event_info['title'] = f"YTU Event {key}"
                
                # Add to events list
                events.append(event_info)
        
        # Final attempt to parse directly from the complete page using regex patterns
        if not events:
            page_text = soup.get_text()
            
            # Look for patterns like "Saat : XX:XX" followed by "Yer : Location"
            time_matches = re.finditer(r'Saat\s*:\s*(\d{1,2}:\d{2})', page_text)
            
            for time_match in time_matches:
                time_text = time_match.group(1)
                position = time_match.end()
                
                # Look for location pattern after this time
                location_match = re.search(r'Yer\s*:\s*([^\n]+)', page_text[position:position+200])
                location_text = location_match.group(1) if location_match else ""
                
                # Look for potential title before the time
                title_match = re.search(r'([^\n]{10,100})\s*Saat\s*:', page_text[max(0, position-150):position])
                title_text = title_match.group(1).strip() if title_match else f"Etkinlik - {time_text}"
                
                # Extract date if present
                date_match = re.search(r'(\d{1,2}[./]\d{1,2}[./]\d{4}|\d{1,2}\s+\w+\s+\d{4})', 
                                     page_text[position-100:position+100])
                date_text = date_match.group(1) if date_match else ""
                
                events.append({
                    'title': title_text,
                    'url': '',
                    'date': date_text,
                    'time': time_text,
                    'location': location_text,
                    'description': f"Bu etkinlik {time_text} saatinde {location_text} yerinde gerçekleşecektir."
                })
        
        # Process and normalize events
        processed_events = []
        for event in events:
            # Create a combined title if the title is missing or just contains time/location
            if not event['title'] or event['title'].startswith('Saat :') or event['title'].startswith('Yer :'):
                elements = []
                if event.get('time') and event['time'] != '':
                    time_str = event['time'].replace('Saat :', '').strip()
                    elements.append(f"Etkinlik {time_str}")
                if event.get('location') and event['location'] != '':
                    loc_str = event['location'].replace('Yer :', '').strip()
                    elements.append(f"- {loc_str}")
                
                event['title'] = " ".join(elements) if elements else "YTU Etkinlik"
            
            # Create combined description
            description_parts = []
            if event.get('date') and event['date'] != '' and event['date'] != 'Date not found':
                description_parts.append(f"Tarih: {event['date']}")
            if event.get('time') and event['time'] != '':
                time_str = event['time'].replace('Saat :', '').strip()
                description_parts.append(f"Saat: {time_str}")
            if event.get('location') and event['location'] != '':
                loc_str = event['location'].replace('Yer :', '').strip()
                description_parts.append(f"Yer: {loc_str}")
            if event.get('description') and event['description'] != '':
                description_parts.append(event['description'])
            
            event['combined_description'] = "\n\n".join(description_parts)
            
            # Add to processed events
            processed_events.append(event)
        
        return processed_events
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def find_parent_container(element, max_levels=3):
    """Find a potential parent container for an event element"""
    current = element
    for _ in range(max_levels):
        if current.parent:
            current = current.parent
            # Check if this parent might be an event container
            if (current.name in ['div', 'article', 'section'] and 
                len(list(current.find_all(['div', 'p', 'span'], recursive=False))) >= 2):
                return current
    
    return None

def extract_event_from_container(container):
    """Extract event information from a container element"""
    event_info = {
        'title': '',
        'url': '',
        'date': '',
        'time': '',
        'location': '',
        'description': ''
    }
    
    # Extract time information
    time_elem = container.find(lambda tag: tag.name in ['div', 'span', 'p'] and 'Saat :' in tag.text)
    if time_elem:
        event_info['time'] = time_elem.get_text(strip=True)
    
    # Extract location information
    location_elem = container.find(lambda tag: tag.name in ['div', 'span', 'p'] and 'Yer :' in tag.text)
    if location_elem:
        event_info['location'] = location_elem.get_text(strip=True)
    
    # Try to extract title
    title_candidates = [
        container.find('h1'), container.find('h2'), container.find('h3'),
        container.find('h4'), container.find('strong'), container.find('b')
    ]
    
    for candidate in title_candidates:
        if candidate and candidate.get_text(strip=True):
            text = candidate.get_text(strip=True)
            if 'Saat :' not in text and 'Yer :' not in text:
                event_info['title'] = text
                break
    
    # If no title found, use the first substantial text
    if not event_info['title']:
        paragraphs = container.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 10 and 'Saat :' not in text and 'Yer :' not in text:
                event_info['title'] = text[:100]
                break
    
    # Extract URL
    link = container.find('a')
    if link and link.has_attr('href'):
        url = link['href']
        if url.startswith('/'):
            url = 'https://www.yildiz.edu.tr' + url
        event_info['url'] = url
    
    # Look for date information
    date_patterns = [
        r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
        r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
        r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
        r'\d{1,2} \w+ \d{4}'         # DD Month YYYY
    ]
    
    text = container.get_text()
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            event_info['date'] = match.group(0)
            break
    
    return event_info

def find_date_near_element(element):
    """Find date information near an element"""
    # Check the element itself
    text = element.get_text()
    date_patterns = [
        r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
        r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
        r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
        r'\d{1,2} \w+ \d{4}'         # DD Month YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    # Check siblings
    if element.parent:
        siblings = list(element.parent.contents)
        for sibling in siblings:
            if hasattr(sibling, 'get_text'):
                text = sibling.get_text()
                for pattern in date_patterns:
                    match = re.search(pattern, text)
                    if match:
                        return match.group(0)
    
    return ''

def find_time_near_element(element):
    """Find time information near an element"""
    # Check the element and nearby elements for time information
    
    # Check the element itself
    if 'Saat :' in element.get_text():
        return element.get_text(strip=True)
    
    # Check nearby elements
    if element.parent:
        time_elem = element.parent.find(lambda tag: tag.name in ['div', 'span', 'p'] and 'Saat :' in tag.text)
        if time_elem:
            return time_elem.get_text(strip=True)
    
    # Look in surrounding area
    surrounding = element.find_next(lambda tag: tag.name in ['div', 'span', 'p'] and 'Saat :' in tag.text)
    if surrounding:
        return surrounding.get_text(strip=True)
    
    return ''

def find_location_near_element(element):
    """Find location information near an element"""
    # Check the element and nearby elements for location information
    
    # Check the element itself
    if 'Yer :' in element.get_text():
        return element.get_text(strip=True)
    
    # Check nearby elements
    if element.parent:
        loc_elem = element.parent.find(lambda tag: tag.name in ['div', 'span', 'p'] and 'Yer :' in tag.text)
        if loc_elem:
            return loc_elem.get_text(strip=True)
    
    # Look in surrounding area
    surrounding = element.find_next(lambda tag: tag.name in ['div', 'span', 'p'] and 'Yer :' in tag.text)
    if surrounding:
        return surrounding.get_text(strip=True)
    
    return ''

def find_title_near_element(element):
    """Find potential title near an element"""
    # Check if there's a heading element nearby
    if element.parent:
        title_elem = element.parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if 'Saat :' not in title_text and 'Yer :' not in title_text:
                return title_text
    
    # Look in surrounding area
    prev_heading = element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5'])
    if prev_heading:
        title_text = prev_heading.get_text(strip=True)
        if 'Saat :' not in title_text and 'Yer :' not in title_text:
            return title_text
    
    return ''

def dom_distance(elem1, elem2):
    """Calculate an approximate 'distance' between two elements in the DOM"""
    # This is a simple heuristic, not a true DOM distance
    # We'll use element positions as a proxy
    try:
        pos1 = str(elem1).find(str(elem1.get_text()))
        pos2 = str(elem2).find(str(elem2.get_text()))
        return abs(pos1 - pos2)
    except:
        return 1000  # Large default distance if calculation fails

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
            print(f"Date: {event.get('date', '')}")
            print(f"Time: {event.get('time', '')}")
            print(f"Location: {event.get('location', '')}")
            if event.get('combined_description'):
                print(f"Description: {event['combined_description']}")
            print("-" * 50)
    else:
        print("No events found. Cannot generate RSS feed.")