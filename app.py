import re, heapq, time
from collections import Counter
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

REG = "FA23-BDS-055"
SOURCE = "Wired Magazine"
app = Flask(__name__)


def make_driver():
    o = Options()
    o.binary_location = "/usr/bin/chromium"
    for a in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
              "--window-size=1920,1080", "--disable-gpu",
              "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36"]:
        o.add_argument(a)
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=o)


def first_story_url(d, timeout=30):
    """Read the first article link with JavaScript (avoids stale element errors)."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            hrefs = d.execute_script(
                "return Array.from(document.querySelectorAll(\"a[href*='/story/']\"))"
                ".map(a => a.href);")
            if hrefs:
                return hrefs[0]
        except Exception:
            pass
        time.sleep(1)
    return ""


def article_text(d, timeout=30):
    """Collect paragraph text with JavaScript, retrying until text appears."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            text = d.execute_script(
                "return Array.from(document.querySelectorAll('p'))"
                ".map(p => p.innerText).filter(t => t.length > 40).join(' ');")
            if text and len(text) > 200:
                return text
        except Exception:
            pass
        time.sleep(1)
    return ""


def summarize(text, n=3):
    sents = re.split(r'(?<=[.!?])\s+', text)
    words = re.findall(r'\w+', text.lower())
    freq = Counter(w for w in words if len(w) > 3)
    score = {s: sum(freq.get(w, 0) for w in re.findall(r'\w+', s.lower())) / (len(s.split()) + 1)
             for s in sents if 5 < len(s.split()) < 60}
    top = heapq.nlargest(n, score, key=score.get)
    return " ".join(s for s in sents if s in top)


@app.route("/")
def home():
    return f"<h1>Registration: {REG}</h1><p>News source: {SOURCE}</p><p>Use /get?keyword=ai</p>"


@app.route("/get")
def get():
    kw = request.args.get("keyword", "")
    url, summary = "", ""
    d = make_driver()
    try:
        d.get(f"https://www.wired.com/search/?q={kw}")
        url = first_story_url(d)
        if not url:
            raise Exception("no article link found on search page")
        d.get(url)
        text = article_text(d)
        if not text:
            raise Exception("could not read article text")
        summary = summarize(text)
    except Exception as e:
        summary = f"error: {e}"
    finally:
        d.quit()
    return jsonify({"registration": REG, "newssource": SOURCE,
                    "keyword": kw, "url": url, "summary": summary})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
