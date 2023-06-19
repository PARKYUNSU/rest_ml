import pandas as pd
import numpy as np

#API URL
import requests, xmltodict, json
import pandas as pd
from pandas import json_normalize
import time

#Selenium (pip install selenium==3.141.0)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm

#DB저장
import sqlite3
import json


key = 'F1PxsM1TEq%2B32cW6lMNrbv7fcFM4E0M4IhBSl1Q%2B3JJLsQ3K73dxBEnFyC56W0mypxfhyOOCpCIV7RnVERTjpA%3D%3D'
url = 'https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong?divId=signguCd&key=11500&indsLclsCd=I2&numOfRows=7000&pageNo=1&type=xml&serviceKey={}'.format(key)

page = 1
total_pages = 6

df_list = []

# 중복 값을 제거하기 위해 set 자료형을 활용합니다.
unique_data = set()
selected_data = [] 
while page <= total_pages:
    page_url = url + '&pageNo=' +str(page)
    content = requests.get(page_url).content
    time.sleep(1.5)

    dict = xmltodict.parse(content)
    jsonString = json.dumps(dict['response']['body']['items']['item'], ensure_ascii=False)
    jsonObject = json.loads(jsonString)
    
    # 가져온 데이터를 처리하여 중복 값을 제거합니다.
    for item in jsonObject:
        # 중복된 값인지 확인하여 제외합니다.
        key = (item.get('bizesNm'), item.get('rdnm'))
        if key not in unique_data:
            unique_data.add(key)
            
            selected_item = {
                'nm': item.get('bizesNm'),
                'rm': item.get('rdnm'),
                'inds': item.get('indsLclsNm').replace('/', ' ') + ' ' + item.get('indsMclsNm').replace('/', ' ') + ' ' + item.get('indsSclsNm').replace('/', ' '),
                'sm': item.get('ksicNm'),
                'dm': item.get('adongNm'),
                'lon': item.get('lon'),
                'lat': item.get('lat')
            }
            selected_data.append(selected_item)

    if not jsonObject:
        break

    df = pd.json_normalize(selected_data)
    df_list.append(df)

    page += 1

new_df = pd.concat(df_list, ignore_index=True)

# 크롬 꺼짐 방지 및 크롬창 비활성화
chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

# 웹드라이버 실행
driver = webdriver.Chrome(options=chrome_options, executable_path='./chromedriver')
driver.implicitly_wait(1)
# 크롬 버전 114.0.5735.106(공식 빌드) (arm64) / mac os

new_df['keyword'] = new_df['dm'] +'%20' + new_df['nm']# %20 - html 공백
new_df['map_url'] = ''

for i, keyword in enumerate(new_df['keyword'].tolist()):
    print("이번에 찾을 키워드 :", i, f"/ {new_df.shape[0] -1} 행", keyword)
    try:
        map_search_url = f"https://m.map.naver.com/search2/search.naver?query={keyword}&sm=hty&style=v5"
        
        driver.get(map_search_url)
        time.sleep(2)
        new_df.iloc[i,-1] = driver.find_element_by_css_selector("#ct > div.search_listview._content._ctList > ul > li:nth-child(1) > div.item_info > a.a_item.a_item_distance._linkSiteview").get_attribute('data-cid')
        # 네이버 지도 시스템은 data-cid에 url 파라미터를 저장해두고 있었습니다.
        # data-cid 번호를 뽑아두었다가 기본 url 템플릿에 넣어 최종적인 url을 완성하면 됩니다.
        
    #검색결과없을시
    except Exception as e1:
        if "li:nth-child(1)" in str(e1): 
            try:
                new_df.iloc[i,-1] = driver.find_element_by_css_selector("#ct > div.search_listview._content._ctList > ul > li:nth-child(1) > div.item_info > a.a_item.a_item_distance._linkSiteview").get_attribute('data-cid')
                time.sleep(1)
            except Exception as e2:
                print(e2)
                new_df.iloc[i,-1] = np.nan
                time.sleep(1)
        else:
            pass

driver.quit()


# 이때 수집한 것은 완전한 URL이 아니라 URL에 들어갈 ID (data-cid 라는 코드명으로 저장된) 이므로, 온전한 URL로 만들어줍니다

new_df['map_url'] = "https://m.place.naver.com/restaurant/" + new_df['map_url']


# URL이 수집되지 않은 데이터는 제거합니다.
new_df = new_df.loc[~new_df['map_url'].isnull()]

# # 각 데이터들을 미리 리스트에 담은 다음, 마지막에 데이터 프레임에 합칠 것입니다.

rest_type_list = []
blog_review_list = []
blog_review_qty_list = []
visitor_review_qty_list = []
star_score_list = []

# 메인 드라이버 : 별점 등을 크롤링
driver = webdriver.Chrome(options=chrome_options, executable_path='./chromedriver')

# 서브 드라이버 : 블로그 리뷰 텍스트를 리뷰 탭 들어가서 크롤링
sub_driver = webdriver.Chrome(options=chrome_options, executable_path='./chromedriver')

for i, url in enumerate(tqdm(new_df['map_url'])):

    driver.get(url)
    sub_driver.get(url+"/review/ugc")
    time.sleep(4)


    try:

        # 간단 정보 가져오기
        
        # 식당 유형 분류
        rest_type = driver.find_element_by_css_selector("#_title > span.DJJvD").text

        # 블로그 리뷰 수
        blog_review_qty = driver.find_element_by_css_selector("#app-root > div > div > div > div.place_section.OP4V8 > div.zD5Nm > div.dAsGb > span:nth-child(3) > a > em").text

        # 블로그 별점 점수
        visitor_review_qty = driver.find_element_by_css_selector("#app-root > div > div > div > div.place_section.OP4V8 > div.zD5Nm > div.dAsGb > span:nth-child(2) > a > em").text

        # 방문자 리뷰 수
        stars_score = driver.find_element_by_css_selector("#app-root > div > div > div > div.place_section.OP4V8 > div.zD5Nm > div.dAsGb > span.PXMot.LXIwF > em").text
       

        # 블로그 리뷰 텍스트 가져오기
        review_text_list = [] # 임시 선언

        
        # 네이버 지도 블로그 리뷰 탭은 동적 웹사이트의 순서가 주문하기, 메뉴보기 등의 존재 여부로 다르기 때문에 css selector가 아니라 element 찾기로 진행
        review_text_crawl_list = sub_driver.find_elements_by_class_name("PRq7t")
        
        # find element's' 메소드를 통해 가져온 내용은 리스트로 저장되고, 리스트 타입을 풀어서(for문 사용) 임시 데이터에 모아 두어야 한다
        for review_crawl_data in review_text_crawl_list:
            review_text_list.append(review_crawl_data.find_element_by_tag_name('div').text)
        
        # 그 리스트에 저장된 텍스트 (한 식당에 대한 여러 리뷰들)를 한 텍스트 덩어리로 모아(join)줍니다.
        review_text = ','.join(review_text_list)


        blog_review_list.append(review_text)

        rest_type_list.append(rest_type)
        blog_review_qty_list.append(blog_review_qty)
        visitor_review_qty_list.append(visitor_review_qty)
        star_score_list.append(stars_score)

    # 리뷰가 없는 업체는 크롤링에 오류가 뜨므로 표기해둡니다.
    except Exception as e1:
        print(f"{i}행 문제가 발생")
        
        # 리뷰가 없으므로 null을 임시로 넣어줍니다.
        blog_review_list.append('null')  
        rest_type_list.append('null')
        blog_review_qty_list.append('null')
        visitor_review_qty_list.append('null')
        star_score_list.append('null')

driver.quit()
sub_driver.quit()


new_df['typeOfRest'] = rest_type_list  #식당 유형
new_df['StarScore'] = star_score_list  # 네이버 별점
new_df['VisitReviewCount'] = visitor_review_qty_list  #식당 방문객 리뷰 수
new_df['BlogReviewCount'] = blog_review_qty_list  #블로그 리뷰 수
new_df['BlogReviewText'] = blog_review_list  #네이버 블로그 리뷰 텍스트


# 크롤링 에러가 떠서 'null'을 넣어 둔 데이터는 활용 의미가 없으므로 행 삭제를 해줘도 됩니다
new_df = new_df.loc[~(new_df['typeOfRest'].str.contains('null'))]


#별점 평균, 수 같은 데이터 역시 스트링 타입으로 크롤링이 되었으므로 numeric으로 바꿔줍니다.
new_df[['VisitReviewCount', 'StarScore', 'BlogReviewCount']] = new_df[['VisitReviewCount', 'StarScore', 'BlogReviewCount']].replace(',', '', regex=True).apply(pd.to_numeric)

new_df = new_df.drop_duplicates()
#df to json
json_data = new_df.to_json(orient='records')

conn = sqlite3.connect('project4_1.db')
cur = conn.cursor()

# 데이터베이스에 테이블이 없는 경우에만 테이블 생성
create_table_query = """
    CREATE TABLE IF NOT EXISTS new_df (
        nm TEXT,
        rm TEXT, 
        inds TEXT,
        sm TEXT,
        dm TEXT,
        lon FLOAT,
        lat FLOAT,
        keyword TEXT,
        map_url TEXT,
        typeOfRest TEXT,
        StarScore REAL,
        VisitReviewCount INTEGER,
        BlogReviewCount INTEGER,
        BlogReviewText TEXT
    )
"""
cur.execute(create_table_query)

# JSON 데이터를 SQLite에 삽입하는 쿼리를 준비합니다.
insert_query = """
    INSERT INTO new_df (nm, rm, inds, sm, dm, lon, lat, keyword, map_url, typeOfRest,
                        StarScore, VisitReviewCount, BlogReviewCount, BlogReviewText)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# JSON 데이터를 레코드 단위로 삽입합니다.
for record in new_df.to_dict(orient='records'):
    values = tuple(record.values())
    cur.execute(insert_query, values)

# 트랜잭션을 커밋합니다.
conn.commit()

# 데이터베이스 연결을 닫습니다.
conn.close()