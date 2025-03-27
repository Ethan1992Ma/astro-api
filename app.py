from flask import Flask, request, render_template, jsonify
import swisseph as swe
import datetime
import os

app = Flask(__name__)

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
        elif cusps[i] > cusps[next_i]:
            if degree >= cusps[i] or degree < cusps[next_i]:
                return i + 1
    return 12

# 相位計算
def calculate_aspects(results):
    aspects = {
        "Conjunction": 0,
        "Opposition": 180,
        "Trine": 120,
        "Square": 90,
        "Sextile": 60
    }
    orb = 3  # 容許度
    aspect_list = []
    keys = list(results.keys())

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            obj1, obj2 = keys[i], keys[j]
            deg1, deg2 = results[obj1]["degree"], results[obj2]["degree"]
            if deg1 is None or deg2 is None:
                continue
            angle = abs(deg1 - deg2)
            if angle > 180:
                angle = 360 - angle
            for asp_name, asp_deg in aspects.items():
                if abs(angle - asp_deg) <= orb:
                    aspect_list.append({
                        "between": f"{obj1} - {obj2}",
                        "aspect": asp_name,
                        "angle": round(angle, 2)
                    })
    return aspect_list

# 宮主星分配
def calculate_house_rulers(houses, results):
    rulers = {
        "牡羊座": "Mars", "金牛座": "Venus", "雙子座": "Mercury", "巨蟹座": "Moon",
        "獅子座": "Sun", "處女座": "Mercury", "天秤座": "Venus", "天蠍座": "Pluto",
        "射手座": "Jupiter", "摩羯座": "Saturn", "水瓶座": "Uranus", "雙魚座": "Neptune"
    }

    house_rulers = {}
    for i in range(12):
        cusp_deg = houses[i]
        sign = get_sign(cusp_deg)
        ruler = rulers.get(sign)
        if ruler and results.get(ruler):
            r_deg = results[ruler]["degree"]
            r_sign = get_sign(r_deg)
            r_house = find_house(r_deg, houses)
        else:
            r_sign, r_house = "未知", "未知"
        house_rulers[f"House {i+1}"] = {
            "sign_on_cusp": sign,
            "ruler": ruler,
            "ruler_sign": r_sign,
            "ruler_house": r_house
        }
    return house_rulers

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/astro', methods=['POST'])
def calculate_chart():
    data = request.json
    birth_date = data['birth_date']
    birth_time = data['birth_time']
    lat = float(data['latitude'])
    lon = float(data['longitude'])

    year, month, day = map(int, birth_date.split('-'))
    hour, minute = map(int, birth_time.split(':'))
    timezone = 8

    jd = swe.julday(year, month, day, hour - timezone + minute / 60.0)
    houses, ascmc = swe.houses(jd, lat, lon, b'P')
    asc = ascmc[0]
    mc = ascmc[1]

    planet_ids = {
        "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY,
        "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO, "Chiron": 15, "Ceres": 17,
        "Pallas": 19, "Juno": 21, "Vesta": 4, "Lilith": 118
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

    # 計算北交點與南交點
    mean_node, _ = swe.calc_ut(jd, swe.MEAN_NODE)
    rahu_deg = mean_node[0]
    ketu_deg = (rahu_deg + 180) % 360
    results["Rahu"] = {
        "degree": round(rahu_deg, 2),
        "sign": get_sign(rahu_deg),
        "house": find_house(rahu_deg, houses)
    }
    results["Ketu"] = {
        "degree": round(ketu_deg, 2),
        "sign": get_sign(ketu_deg),
        "house": find_house(ketu_deg, houses)
    }

    # 福點 Part of Fortune (簡化公式：Asc + Moon - Sun)
    sun = results["Sun"]["degree"]
    moon = results["Moon"]["degree"]
    asc_deg = asc
    pof = (asc_deg + moon - sun) % 360
    results["Part of Fortune"] = {
        "degree": round(pof, 2),
        "sign": get_sign(pof),
        "house": find_house(pof, houses)
    }

    aspects = calculate_aspects(results)
    house_rulers = calculate_house_rulers(houses, results)

    return jsonify({
        "ascendant": round(asc, 2),
        "midheaven": round(mc, 2),
        "planets": results,
        "aspects": aspects,
        "house_rulers": house_rulers
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
