from flask import Flask, render_template, request, redirect
import folium
import sqlite3

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import pickle
from model import find_simi_place
import json

app = Flask(__name__)
model = pickle.load(open('model.pkl', 'rb'))

@app.route('/')
def base():
    map = folium.Map(
        location=[37.553685, 126.825084],
        zoom_start=14)  # 서울 강서구 지도 13배
    
    folium.Marker(
    location=[37.562587, 126.825864],
    icon=folium.DivIcon(
        icon_size=(150, 36),
        icon_anchor=(75, 45),
        html='<div style="font-size: 45px;"><b>강서구</b></div>',
    )).add_to(map) #지도에 강서구 이름 넣기


    geojson_layer = folium.GeoJson('./gangseoDong.geojson', name='강서구',
                                   style_function=lambda feature: {
                                       'fillColor': '#4285F4',  # 연한 하늘색으로 설정
                                       'fillOpacity': 0.3,  # 투명도 조정
                                       'color': '#4285F4',  # 테두리 색상 설정
                                       'weight': 3  # 테두리 두께 설정
                                   })
    geojson_layer.add_to(map)

    search_placeholder = "검색어를 입력하세요"  # 검색창의 placeholder 텍스트

    return render_template('index.html', map=map._repr_html_(), search_placeholder=search_placeholder)

@app.route('/search', methods=['POST'])
def search():
    place_name = request.form.get('place_name')  # place_name 값을 가져옵니다.
    if place_name:
        # 유사한 장소 검색
        results = model(place_name, top_n=4)

        # 기본 지도 생성과 강서구 마커, GeoJson 레이어 설정 부분
        map = folium.Map(location=[37.553685, 126.825084], zoom_start=14)
        folium.Marker(
            location=[37.562587, 126.825864],
            icon=folium.DivIcon(
                icon_size=(150, 36),
                icon_anchor=(75, 45),
                html='<div style="font-size: 45px;"><b>강서구</b></div>'
            )
        ).add_to(map)  # 지도에 강서구 이름 넣기

        # 강서구 GeoJson 파일 읽기
        with open('./gangseoDong.geojson', 'r', encoding='utf-8') as f:
            gangseo_geojson = json.load(f)

        geojson_layer = folium.GeoJson(
            gangseo_geojson,
            name='강서구',
            style_function=lambda feature: {
                'fillColor': '#4285F4',
                'fillOpacity': 0.1,
                'color': '#4285F4',
                'weight': 3
            }
        )
        geojson_layer.add_to(map)

        map_html = map._repr_html_()

        if results:
            return render_template('search.html', place_name=place_name, results=results, map=map_html,
                                   gangseo_geojson=gangseo_geojson)
        else:
            return render_template('search.html', place_name=place_name, message='검색 결과가 없습니다.',
                                   gangseo_geojson=gangseo_geojson)

    return render_template('search.html')


if __name__ == '__main__':
     app.run(debug=True)