from flask import Flask, request, render_template, jsonify
import swisseph as swe
import datetime
import os
import urllib.request
import sys

app = Flask(__name__)

# ========== 自動下載 Swiss Ephemeris 星曆檔 ==========
EPHE_DIR = "ephe"
EPHE_FILES = [
    ("sepl_18.se1", "https://www.astro.com/ftp/swisseph/ephe/sepl_18.se1"),
    ("semo_18.se1", "https://www.astro.com/ftp/swisseph/ephe/semo_18.se1")
]

os.makedirs(EPHE_DIR, exist_ok=True)
for filename, url in EPHE_FILES:
    path = os.path.join(EPHE_DIR, filename)
    if not os.path.exists(path):
        try:
            print(f"🔽 正在下載 {filename}...")
            urllib.request.urlretrieve(url, path)
            print(f"✅ 下載完成：{filename}")
        except Exception as e:
            print(f"❌ 下載 {filename} 失敗：{e}")
            sys.exit(f"無法下載 {filename}，中止啟動伺服器。")

swe.set_ephe_path(EPHE_DIR)

# ========== 星座與宮位計算邏輯 ==========
ZODIAC = ["牡羊座", "金牛座", "雙子座", "巨蟹座", "獅子座", "處女座", "天秤座", "天蠍座", "射手座", "摩羯座", "水瓶座", "雙魚座"]

# 判斷星座
def get_sign(degree):
    return ZODIAC[int(degree // 30)]

# 判斷宮位
def find_house(degree, cusps):
    for i in range(12):
        next_i = (i + 1) % 12
        if cusps[i] <= degree < cusps[next_i]:
            return i + 1
        elif cusps[i] > cusps[next_i]:  # 跨越 360/0 度
            if degree >= cusps[i] or degree < cusps[next_i]:
                return i + 1
    return 12

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/astro', methods=['POST'])
def calculate_chart():
    data = request.json
    birth_date = data['birth_date']  # YYYY-MM-DD
    birth_time = data['birth_time']  # HH:MM
    lat = float(data['latitude'])
    lon = float(data['longitude'])

    year, month, day = map(int, birth_date.split("-"))
    hour, minute = map(int, birth_time.split(":"))
    timezone = 8  # 預設為台灣時區

    jd = swe.julday(year, month, day, hour - timezone + minute / 60.0)
    houses, ascmc = swe.houses(jd, lat, lon, b'P')
    asc = ascmc[0]
    mc = ascmc[1]

    planet_ids = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
        "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO
    }

    results = {}
    for name, pid in planet_ids.items():
        pos, _ = swe.calc_ut(jd, pid)
        degree = pos[0]
        sign = get_sign(degree)
        house = find_house(degree, houses)
        results[name] = {
            "degree": round(degree, 2),
            "sign": sign,
            "house": house
        }

    return jsonify({
        "ascendant": round(asc, 2),
        "midheaven": round(mc, 2),
        "planets": results,
        "aspects": "(尚未實作)",
        "house_rulers": "(尚未實作)"
    })

# ========== 設定埠口與啟動 Flask ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
