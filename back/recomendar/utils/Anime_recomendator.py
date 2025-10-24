import pandas as pd

a_col = ['anime_id', 'name','members']
animes = pd.read_csv('anime.csv', sep=',', usecols=a_col)

ratings = pd.read_csv('ratings_clean_1.csv', sep=',')


ratings.head()

userRatings = ratings.pivot_table(index='user_id',columns='anime_id',values='rating')

userRatings.head()

corrMatrix = userRatings.corr(method='pearson', min_periods=10)
corrMatrix.head()

print(corrMatrix.shape)
mis_reviews = pd.DataFrame({
    'user_id': [999],  
    'anime_id': [9253],  
    'rating': [10]  
})
mis_reviews.to_csv('data/my_ratings.csv', index=False)
mis_ratings = pd.merge(ratings, mis_reviews[['anime_id', 'rating']])
myRatings = pd.Series(data=mis_ratings['rating'].values, index=mis_ratings['anime_id'])


simCandidates = pd.Series(dtype=float)

for anime, rating in myRatings.items():
    if anime not in corrMatrix.columns:
        continue  # ignora si el anime no está en la matriz
    sims = corrMatrix[anime].dropna()
    sims = sims.map(lambda x: x * rating)
    simCandidates = pd.concat([simCandidates, sims])

simCandidates = simCandidates.groupby(simCandidates.index).sum()
simCandidates = simCandidates.drop(myRatings.index, errors='ignore')
simCandidates = simCandidates.sort_values(ascending=False)


    
simdf = simCandidates.reset_index()
simdf.columns = ['anime_id','score']
recomendaciones = pd.merge(simdf, animes, on='anime_id', how='left')
recomendaciones.sort_values('score', ascending=False, inplace=True)
print(recomendaciones[['name', 'score']].head(10))

