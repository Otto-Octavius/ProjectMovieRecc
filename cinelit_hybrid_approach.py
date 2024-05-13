# -*- coding: utf-8 -*-
"""Cinelit-hybrid-approach.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1hTolFZNB8DJLWytI8dSYDnY6iaGbeTmB
"""

import pandas as pd
import numpy as np
import warnings
from sklearn.preprocessing import MinMaxScaler
from ast import literal_eval
import string
import re
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

warnings.filterwarnings('ignore')

def get_text(text, obj='name'):
    text = literal_eval(text)

    if len(text) == 1:
        for i in text:
            return i[obj]
    else:
        s = []
        for i in text:
            s.append(i[obj])
        return ', '.join(s)
    
def separate(text):
    clean_text = []
    for t in text.split(','):
        cleaned = re.sub('\(.*\)', '', t) # Remove text inside parentheses
        cleaned = cleaned.translate(str.maketrans('','', string.digits))
        cleaned = cleaned.replace(' ', '')
        cleaned = cleaned.translate(str.maketrans('','', string.punctuation)).lower()
        clean_text.append(cleaned)
    return ' '.join(clean_text)

def remove_punc(text):
    cleaned = text.translate(str.maketrans('','', string.punctuation)).lower()
    clean_text = cleaned.translate(str.maketrans('','', string.digits))
    return clean_text

def book_cat(x):
    cat = x['title'] +" "+ x["original_title"]+" "+x["description"]+" "+" ".join(x['tag_name'])+" "+x["authors"]
    return cat

credits = pd.read_csv('/archive/credits.csv')
keywords = pd.read_csv('/archive/keywords.csv')
movies = pd.read_csv('/archive/movies_metadata.csv').\
                     drop(['belongs_to_collection', 'homepage', 'imdb_id', 'poster_path', 'status', 'title', 'video'], axis=1).\
                     drop([19730, 29503, 35587])

movies['id'] = movies['id'].astype('int64')
df = movies.merge(keywords, on='id').\
     merge(credits, on='id')
df['original_language'] = df['original_language'].fillna('')
df['runtime'] = df['runtime'].fillna(0)
df['tagline'] = df['tagline'].fillna('')

df.dropna(inplace=True)

df['genres'] = df['genres'].apply(get_text)
df['production_companies'] = df['production_companies'].apply(get_text)
df['production_countries'] = df['production_countries'].apply(get_text)
df['crew'] = df['crew'].apply(get_text)
df['spoken_languages'] = df['spoken_languages'].apply(get_text)
df['keywords'] = df['keywords'].apply(get_text)
df['characters'] = df['cast'].apply(get_text, obj='character')
df['actors'] = df['cast'].apply(get_text)

df.drop('cast', axis=1, inplace=True)
df = df[~df['original_title'].duplicated()]
df = df.reset_index(drop=True)

df['release_date'] = pd.to_datetime(df['release_date'])
df['budget'] = df['budget'].astype('float64')
df['popularity'] = df['popularity'].astype('float64')

R = df['vote_average']
v = df['vote_count']
m = df['vote_count'].quantile(0.8)
C = df['vote_average'].mean()

df['weighted_average'] = (R*v + C*m)/(v+m)

scaler = MinMaxScaler()
scaled = scaler.fit_transform(df[['popularity', 'weighted_average']])
weighted_df = pd.DataFrame(scaled, columns=['popularity', 'weighted_average'])

weighted_df.index = df['original_title']

weighted_df['score'] = weighted_df['weighted_average']*0.4 + weighted_df['popularity'].astype('float64')*0.6

weighted_df_sorted = weighted_df.sort_values(by='score', ascending=False)

hybrid_df = df[['original_title', 'adult', 'genres', 'overview', 'production_companies', 'tagline', 'keywords', 'crew', 'characters', 'actors']]

hybrid_df['adult'] = hybrid_df['adult'].apply(remove_punc)
hybrid_df['genres'] = hybrid_df['genres'].apply(remove_punc)
hybrid_df['overview'] = hybrid_df['overview'].apply(remove_punc)
hybrid_df['production_companies'] = hybrid_df['production_companies'].apply(separate)
hybrid_df['tagline'] = hybrid_df['tagline'].apply(remove_punc)
hybrid_df['keywords'] = hybrid_df['keywords'].apply(separate)
hybrid_df['crew'] = hybrid_df['crew'].apply(separate)
hybrid_df['characters'] = hybrid_df['characters'].apply(separate)
hybrid_df['actors'] = hybrid_df['actors'].apply(separate)

hybrid_df['bag_of_words'] = ''
hybrid_df['bag_of_words'] = hybrid_df['original_title'] + " " + hybrid_df[hybrid_df.columns[1:]].apply(lambda x: ' '.join(x), axis=1)
hybrid_df.set_index('original_title', inplace=True)

hybrid_df = hybrid_df[['bag_of_words']]
hybrid_df.head()

books = pd.read_csv('/content/drive/MyDrive/top2k_book_descriptions.csv', index_col=0)

b = books

books['tag_name'] = books['tag_name'].apply(lambda x: literal_eval(x) if literal_eval(x) else np.nan)
books = books[books['description'].notnull() | books['tag_name'].notnull()]
books = books.fillna('')

books["bag_of_words"] = books.apply(book_cat, axis=1)

books.set_index('original_title', inplace=True)
books = books[['bag_of_words']]

tfidfB = TfidfVectorizer(stop_words='english', min_df=5)
tfidfB_matrix = tfidfB.fit_transform(books['bag_of_words'])
cos_simB = cosine_similarity(tfidfB_matrix)

hybrid_df = weighted_df_sorted[:10000].merge(hybrid_df, left_index=True, right_index=True, how='left')
tfidf = TfidfVectorizer(stop_words='english', min_df=5)
tfidf_matrix = tfidf.fit_transform(hybrid_df['bag_of_words'])
cos_sim = cosine_similarity(tfidf_matrix)

soups = pd.concat([hybrid_df['bag_of_words'],books['bag_of_words']],ignore_index=True)
count = CountVectorizer(stop_words = "english")
count.fit(soups)
movies_matrix = count.transform(hybrid_df['bag_of_words'])
books_matrix = count.transform(books['bag_of_words'])
cosine = cosine_similarity(movies_matrix,books_matrix)

np.save('Books_Cosine.npy', cos_simB)

np.save('Combined_Cosine.npy', cosine)

np.save('Movies_Cosine.npy', cos_sim)

def predict_book(title):
    m = hybrid_df.reset_index()
    indices = pd.Series(m.index, index=m['original_title'].apply(lambda x: x.lower() if x is not np.nan else "")).drop_duplicates()
    idx = indices[title.lower()]
    sim_scores = list(enumerate(cosine[idx]))
    sim_scores = sorted(sim_scores, key=lambda x:x[1], reverse=True)

    sim_scores = sim_scores[:10]

    book_indices = [i[0] for i in sim_scores]
    index_book = books.index.get_loc(books.iloc[book_indices].index[0])
    similarity = cos_simB[index_book].T
    sim_df = pd.DataFrame(similarity, columns=['similarity'])
    final_df = pd.concat([b, sim_df], axis=1)
    final_df_filtered = final_df[final_df['similarity'] >= 0.3]

    if final_df_filtered.empty:
        return "No books available"
    else:
        final_df_sorted = final_df_filtered.sort_values(by='similarity', ascending=False)
        final_df_sorted.set_index('title', inplace=True)
        return final_df_sorted[['similarity']]

def predict_movie(title, similarity_weight=0.7, top_n=10):
    data = hybrid_df.reset_index()
    index_movie = data[data['original_title'] == title].index
    similarity = cos_sim[index_movie].T

    sim_df = pd.DataFrame(similarity, columns=['similarity'])
    final_df = pd.concat([data, sim_df], axis=1)
    final_df['final_score'] = final_df['score']*(1-similarity_weight) + final_df['similarity']*similarity_weight

    final_df_sorted = final_df.sort_values(by='final_score', ascending=False).head(top_n)
    final_df_sorted.set_index('original_title', inplace=True)
    return final_df_sorted[['similarity']]

def main():
    just_finished = input("Enter the movie/book title you just finished: ")

    movie_recommendations = predict_movie(just_finished, similarity_weight=0.7, top_n=5)
    book_recommendations = predict_book(just_finished)

    print("\nMovie Recommendations:")
    print(movie_recommendations)

    print("\nBook Recommendations:")
    print(book_recommendations)

if __name__ == "__main__":
    main()
