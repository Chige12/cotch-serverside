from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import requests
import json
import xmltodict
import urllib.request
import urllib.parse
import urllib
import datetime
from collections import OrderedDict

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

PREFECTURE_CATEGORIES = {
    '大阪府': [
        'たこやき', 'お好み焼き'
    ],
    '京都府': [
        'ラーメン', '茶そば'
    ],
    '兵庫県': [
        '中華'
    ],
}
OTHER_CATEGORIES = [
    'ラーメン', '餃子', '居酒屋', 'イタリアン', 'うどん', 'そば', 'そば'
]
GOOGLE_MAPS_API_KEY = 'X'
HOTPEPPER_API_KEY = 'X'

def dist(origin, destinations):
    # Google Maps Platform Directions API endpoint
    endpoint = 'https://maps.googleapis.com/maps/api/distancematrix/json?'

    request = endpoint + "units=imperial&origins=" + \
        str(origin[0])+","+str(origin[1])+"&destinations="

    for i, target in enumerate(destinations):
        if(i == 0):
            request += str(target[0])+","+str(target[1])
        else:
            request += "|"+str(target[0])+","+str(target[1])
        pass

    request += "&mode=walking&key="+GOOGLE_MAPS_API_KEY

    # Google Maps Platform Directions APIを実行
    response = urllib.request.urlopen(request).read()

    # 結果(JSON)を取得
    directions = json.loads(response)
    # print(directions)
    # print(directions["rows"][0]["elements"])

    reply = []

    for i, target in enumerate(directions["rows"][0]["elements"]):
        if (target["status"] == "NOT_FOUND"):
            reply += [[None, None]]
        elif (i == 0):
            reply += [[str(target["distance"]["value"]),
                       target["duration"]["text"]]]
        else:
            reply += [[str(target["distance"]["value"]),
                       target["duration"]["text"]]]

    return reply

def search_store(longitude, latitude, start, keyword):

    url = 'https://webservice.recruit.co.jp/hotpepper/gourmet/v1/'
    photo_url = 'https://www.hotpepper.jp/s/flash/store_photo_slide/{}/{}.xml'

    payload = {'key':HOTPEPPER_API_KEY, 'lng':longitude, 'lat':latitude, 'start':start, 'count': 10, 'keyword':keyword}
    r = requests.get(url, params=payload)
    xml = r.text
    datas = xmltodict.parse(xml)
    results = []
    if datas['results']['results_returned'] == '0':
        return results
    for data in datas['results']['shop']:
        id = data['id']

        name = data['name']
        lng = data['lng']
        lat = data['lat']
        budget = data['budget']['name']
        catch = data['catch']

        images = []
        r2 = requests.get(photo_url.format(id[-2:], id))
        photo_xml = xmltodict.parse(r2.text)
        try:
            if isinstance(photo_xml['photoSlide']['items']['item'], list):
                for v in photo_xml['photoSlide']['items']['item']:
                    images.append(v['photo'])
            elif isinstance(photo_xml['photoSlide']['items']['item'], OrderedDict):
                images.append(photo_xml['photoSlide']['items']['item']['photo'])
        except:
            pass
        result = {'id': id, 'name':name, 'location': {'longitude':lng, 'latitude':lat}, 'budget':budget, 'catch':catch, 'images':images}

        results.append(result)
    return results


def get_prefecture(longitude, latitude):
    r = requests.get('http://geoapi.heartrails.com/api/json?method=searchByGeoLocation&x={}&y={}'.format(longitude, latitude))
    j = r.json()
    return j['response']['location'][0]['prefecture']

def make_store(store_info, prefecture, category_name):
    store_info['link'] = 'https://www.google.com/maps/?ll={},{}&q={}'.format(store_info['location']['latitude'], store_info['location']['longitude'], urllib.parse.quote(store_info['name']))
    store_info['is_open'] = True
    store_info['category_name'] = category_name
    store_info['prefecture'] = prefecture

    return store_info

@app.route('/search-all')
def search_all():
    longitude = request.args.get('longitude', None)
    latitude = request.args.get('latitude', None)

    if not longitude or not latitude:
        app.logger.debug("{} {}".format(longitude, latitude))
        return abort(jsonify(message='invalid arguments'))

    try:
        prefecture = get_prefecture(longitude, latitude)
    except Exception as e:
        app.logger.debug(e)
        return abort(jsonify(message="failed to get prefecture"))
    if prefecture not in PREFECTURE_CATEGORIES:
        app.logger.debug(prefecture)
        return abort(jsonify(message="invalid longitude/latitude"))


    results = []
    for category in OTHER_CATEGORIES:
        stores = search_store(longitude, latitude, 1, category)
        for store in stores:
            results.append(make_store(store, '', category))

    locations = []
    for result in results:
        locations.append([result['location']['latitude'], result['location']['longitude']])

    times = dist([latitude, longitude], locations)
    for i in range(len(times)):
        results[i]['distance'] = times[i][0]
        results[i]['time'] = times[i][1]

    return jsonify(results)

@app.route('/search')
def search():
    longitude = request.args.get('longitude', None)
    latitude = request.args.get('latitude', None)
    start = request.args.get('start', '1')

    if not longitude or not latitude:
        app.logger.debug("{} {}".format(longitude, latitude))
        return abort(jsonify(message='invalid arguments'))

    try:
        start = int(start)
    except:
        app.logger.debug("start={}".format(start))
        return abort(jsonify(message='invalid arguments'))

    try:
        prefecture = get_prefecture(longitude, latitude)
    except Exception as e:
        app.logger.debug(e)
        return abort(jsonify(message="failed to get prefecture"))
    if prefecture not in PREFECTURE_CATEGORIES:
        app.logger.debug(prefecture)
        return abort(jsonify(message="invalid longitude/latitude"))


    results = []
    for category in PREFECTURE_CATEGORIES[prefecture]:
        stores = search_store(longitude, latitude, start, category)
        for store in stores:
            results.append(make_store(store, prefecture, category))
    locations = []
    for result in results:
        locations.append([result['location']['latitude'], result['location']['longitude']])

    times = dist([latitude, longitude], locations)
    for i in range(len(times)):
        results[i]['distance'] = times[i][0]
        results[i]['time'] = times[i][1]


    return jsonify(results)


@app.route('/')
def index():
    return 'HELLO'

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
