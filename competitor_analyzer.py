import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from collections import Counter


def extract_colors_from_css(text):
    hex_colors = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}', text)
    return list(set(hex_colors))[:15]


def extract_keywords(text):
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stopwords = set([
        "about","their","with","from","this","that","have","your",
        "more","they","will","what","when","where","which","them",
        "privacy","terms","cookie","contact","login","signup"
    ])
    filtered = [w for w in words if w not in stopwords]
    common = Counter(filtered).most_common(20)
    return [w[0] for w in common]


def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def detect_ctas(soup):
    ctas = []
    for tag in soup.find_all(["a", "button"]):
        text = tag.get_text(strip=True).lower()
        if any(phrase in text for phrase in [
            "get started", "try", "sign up",
            "book demo", "contact sales",
            "learn more", "start free"
        ]):
            ctas.append(text)
    return list(set(ctas))[:10]


def detect_product_links(links):
    product_links = []
    for link in links:
        if any(word in link.lower() for word in [
            "product", "solutions", "services",
            "features", "platform", "pricing"
        ]):
            product_links.append(link)
    return list(set(product_links))[:10]


def analyze_competitor_site(start_url, max_depth=2, max_pages=8):

    visited = set()
    to_visit = [(start_url, 0)]
    domain = urlparse(start_url).netloc

    all_text = ""
    all_headings = []
    all_colors = []
    all_ctas = []
    all_product_links = []

    while to_visit and len(visited) < max_pages:
        url, depth = to_visit.pop(0)

        if depth > max_depth or url in visited:
            continue

        try:
            resp = requests.get(
                url,
                timeout=6,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            resp.raise_for_status()
        except:
            continue

        visited.add(url)

        soup = BeautifulSoup(resp.text, "html.parser")

        # Collect links BEFORE removing elements
        links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True)]

        # Remove unnecessary tags
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        page_text = clean_text(soup.get_text(separator=" "))
        all_text += " " + page_text[:1500]

        headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2"])]
        all_headings.extend(headings[:5])

        colors = extract_colors_from_css(resp.text)
        all_colors.extend(colors)

        ctas = detect_ctas(soup)
        all_ctas.extend(ctas)

        product_links = detect_product_links(links)
        all_product_links.extend(product_links)

        if depth < max_depth:
            for link in links:
                parsed = urlparse(link)

                if parsed.netloc == domain and link not in visited:
                    if not any(skip in link.lower() for skip in [
                        "login", "signup", "privacy",
                        "terms", "blog", "careers"
                    ]):
                        to_visit.append((link, depth + 1))

    keywords = extract_keywords(all_text)

    return {
        "pages_scraped": len(visited),
        "top_keywords": keywords,
        "headings": all_headings[:15],
        "detected_colors": list(set(all_colors))[:8],
        "ctas": list(set(all_ctas))[:10],
        "product_links": list(set(all_product_links))[:10],
        "text_sample": all_text[:3000]
    }
