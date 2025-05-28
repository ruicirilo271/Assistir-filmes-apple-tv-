from flask import Flask, render_template, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

app = Flask(__name__)

TMDB_API_KEY = '516adf1e1567058f8ecbf30bf2eb9378'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# Função para verificar se o filme está na Apple TV+ Brasil
def esta_na_apple_tv(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"
    resp = requests.get(url)
    if resp.status_code != 200:
        return False
    data = resp.json()
    # Checar se 'BR' está nos resultados e se Apple TV+ está listado
    br_providers = data.get('results', {}).get('BR', {})
    if not br_providers:
        return False
    # Provedores de streaming
    flatrate = br_providers.get('flatrate', [])
    for provider in flatrate:
        if 'apple' in provider.get('provider_name', '').lower():
            return True
    return False

# Busca filmes populares da Apple TV+
def get_filmes_apple_tv_populares():
    url = f"{TMDB_BASE_URL}/movie/popular?api_key={TMDB_API_KEY}&language=pt-BR&page=1"
    resp = requests.get(url)
    filmes = []
    if resp.status_code != 200:
        return filmes
    data = resp.json()
    count = 0
    for movie in data.get('results', []):
        if count >= 10:
            break
        if esta_na_apple_tv(movie['id']):
            filmes.append({
                'id': movie['id'],
                'title': movie['title'],
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie['poster_path'] else '',
                'overview': movie['overview'],
                'release_date': movie['release_date']
            })
            count +=1
    return filmes

# Pesquisa filmes na Apple TV+ por título
def pesquisar_filmes_apple_tv(search_query):
    url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&language=pt-BR&query={requests.utils.quote(search_query)}&page=1&include_adult=false"
    resp = requests.get(url)
    filmes = []
    if resp.status_code != 200:
        return filmes
    data = resp.json()
    for movie in data.get('results', []):
        if esta_na_apple_tv(movie['id']):
            filmes.append({
                'id': movie['id'],
                'title': movie['title'],
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie['poster_path'] else '',
                'overview': movie['overview'],
                'release_date': movie['release_date']
            })
    return filmes

# Busca no megafilmeshdz.cyou se o filme está lá para assistir
def buscar_filme_megafilmes(titulo):
    search_url = f"https://megafilmeshdz.cyou/?s={titulo.replace(' ', '+')}"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        articles = soup.select("article")
        for article in articles:
            title_tag = article.find("h2")
            if title_tag and titulo.lower() in title_tag.text.lower():
                link_tag = article.find("a", href=True)
                if not link_tag:
                    continue
                filme_url = link_tag['href']
                filme_page = requests.get(filme_url, headers=HEADERS, timeout=10)
                filme_soup = BeautifulSoup(filme_page.text, 'html.parser')
                iframe = filme_soup.find('iframe')
                video_link = iframe['src'] if iframe else None
                return video_link, filme_url
        return None, None
    except Exception:
        return None, None

@app.route('/')
def index():
    search = request.args.get('search', '')
    if search:
        filmes = pesquisar_filmes_apple_tv(search)
    else:
        filmes = get_filmes_apple_tv_populares()
    return render_template('index.html', filmes=filmes, search=search)

@app.route('/filme/<int:movie_id>')
def filme(movie_id):
    # Buscar detalhes TMDb para mostrar info
    url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=pt-BR"
    resp = requests.get(url)
    if resp.status_code != 200:
        return "Filme não encontrado.", 404
    data = resp.json()
    titulo = data.get('title')
    poster_path = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else ''
    overview = data.get('overview')
    release_date = data.get('release_date')

    video_link, filme_url = buscar_filme_megafilmes(titulo)

    return render_template('filme.html', titulo=titulo, poster_path=poster_path, overview=overview, release_date=release_date, video_link=video_link, filme_url=filme_url)

if __name__ == '__main__':
    app.run(debug=True)
