import re, heapq
from collections import Counter
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    d = make_driver()
    try:
        d.get(f"https://www.wired.com/search/?q={kw}")
        link = WebDriverWait(d, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/story/']")))
        url = link.get_attribute("href")
        d.get(url)
        WebDriverWait(d, 20).until(EC.presence_of_element_located((By.TAG_NAME, "p")))
        text = " ".join(p.text for p in d.find_elements(By.TAG_NAME, "p") if len(p.text) > 40)
        summary = summarize(text)
    except Exception as e:
        url, summary = "", f"error: {e}"
    finally:
        d.quit()
    return jsonify({"registration": REG, "newssource": SOURCE,
                    "keyword": kw, "url": url, "summary": summary})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
