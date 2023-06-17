#deepleaning
import pandas as pd
import numpy as np
import joblib
import sqlite3
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

#pickling
import pickle

conn = sqlite3.connect('./project4.db')
query = 'SELECT * FROM new_df'
df = pd.read_sql_query(query, conn)
conn.close()

df = df.drop_duplicates().reset_index(drop=True)

#상권업종명 간의 텍스트 피쳐 백터라이징
count_vect_category = CountVectorizer(min_df=0, ngram_range=(1,2))
place_category = count_vect_category.fit_transform(df['inds'])

#상권업종명 간의 코사인 유사도 따지기
place_simi_cate = cosine_similarity(place_category, place_category)
place_simi_cate_sorted_ind = place_simi_cate.argsort()[:, ::-1]


# 리뷰 텍스트 데이터 간의 텍스트 피쳐 벡터라이징
count_vect_review = CountVectorizer(min_df=2, ngram_range=(1,2))
place_review = count_vect_review.fit_transform(df['BlogReviewText'])

# 리뷰 텍스트 간의 코사인 유사도 따지기
place_simi_review = cosine_similarity(place_review, place_review)
place_simi_review_sorted_ind = place_simi_review.argsort()[:, ::-1]

df['BlogReviewCount'] = np.log1p(df['BlogReviewCount'])
df['VisitReviewCount'] = np.log1p(df['VisitReviewCount'])

# 리뷰 수와 방문자 리뷰 수에 로그 변환 적용

place_simi_co = (
                 + place_simi_cate * 0.3 # 공식 1. 카테고리 유사도
                 + place_simi_review * 1 # 공식 2. 리뷰 텍스트 유사도
                 + np.repeat([df['BlogReviewCount'].values], len(df['BlogReviewCount']) , axis=0) * 0.001  # 공식 3. 블로그 리뷰가 얼마나 많이 올라왔는지
                 + np.repeat([df['StarScore'].values], len(df['StarScore']) , axis=0) * 0.005            # 공식 4. 블로그 별점이 얼마나 높은지
                 + np.repeat([df['VisitReviewCount'].values], len(df['VisitReviewCount']) , axis=0) * 0.001   # 공식 5.방문자 리뷰가 얼마나 많이 됐는지
                 )



place_simi_co_sorted_ind = place_simi_co.argsort()[:, ::-1]

df['BlogReviewCount'] = np.round(np.expm1(df['BlogReviewCount'])).astype(int)
df['VisitReviewCount'] = np.round(np.expm1(df['VisitReviewCount'])).astype(int)

# 최종 구현 함수
def find_simi_place(place_name, top_n=4):
    global df, place_simi_co_sorted_ind  # 전역 변수에 접근하기 위해 global 키워드를 사용합니다.

    place_title = df[df['nm'] == place_name]
    place_index = place_title.index.values
    similar_indexes = place_simi_co_sorted_ind[place_index, :(top_n)]
    similar_indexes = similar_indexes.reshape(-1)
    similar_df = df.iloc[similar_indexes].drop(['keyword', 'BlogReviewText'], axis=1)
    if similar_df.empty:
        filtered_df = df[df['BlogReviewText'].str.contains(place_name)]
        similar_df = filtered_df.nlargest(top_n, ['StarScore', 'VisitReviewCount', 'BlogReviewCount']).drop(
            ['keyword', 'BlogReviewText'], axis=1)
    return similar_df.to_dict('records')

pickle.dump(find_simi_place, open('model.pkl', 'wb'))