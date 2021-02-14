"""Retrieve films from OMDb and check which films are on RYM."""

import os
import re
import time
from contextlib import suppress
from difflib import SequenceMatcher

import omdb
import pandas as pd
from bs4 import BeautifulSoup, SoupStrainer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


def check_movie_list_existence():
    """Check if movie list exists.

    Returns:
        boolean for whether list exists
    """
    return os.path.isfile('movie_list.csv')


def read_movie_list():
    """Read movie list as dataframe.

    Returns:
        movie list as dataframe
    """
    with open('movie_list.csv', 'r'):
        dataframe = pd.read_csv('movie_list.csv')
    return dataframe


def create_movie_list():
    """Create new movie list.

    Returns:
        empty dataframe for new movie list
    """
    return pd.DataFrame(
        columns=[
            'title',
            'year',
            'rated',
            'released',
            'runtime',
            'genre',
            'director',
            'writer',
            'actors',
            'plot',
            'language',
            'country',
            'awards',
            'poster',
            'ratings',
            'metascore',
            'imdb_rating',
            'imdb_votes',
            'imdb_id',
            'type',
            'dvd',
            'box_office',
            'production',
            'website',
            'response',
            'in_rym',
        ],
    )


def get_movie_list():
    """Read dataframe if it exists, else create new one.

    Returns:
        dataframe with movie information
    """
    if check_movie_list_existence():
        movie_list = read_movie_list()
    else:
        movie_list = create_movie_list()
    return movie_list


def get_imdb_string(number):
    """Convert number to IMDB_ID String.

    Args:
        number: number entered

    Returns:
        imdb_id string
    """
    return 'tt{arg}'.format(arg=str(int(number)).zfill(7))


def get_movie(imdb_id, api_key):
    """Get movie from imdb_id.

    Args:
        imdb_id: imdb ID number for movie
        api_key: API key for omdb

    Returns:
        omdb info from imdb_id
    """
    omdb.set_default('apikey', api_key)
    return omdb.imdbid(imdb_id)


def validate_input(start, end):
    """Convert start and end strings to ints.

    Args:
        start: starting value
        end: ending value

    Returns:
        start, end as ints
    """
    try:
        start = int(start)
    except ValueError:
        start = 0

    try:
        end = int(end)
    except ValueError:
        end = 9999999

    return (start, end)


def add_individual_movie(movie, dataframe, api_key):
    """Add individual movie to dataframe.

    Args:
        movie: movie to add
        dataframe: place movie is added to
        api_key: user api key

    Returns:
        updated dataframe
    """
    movie_data = get_movie(movie, api_key)
    return dataframe.append(movie_data, ignore_index=True)


def add_movies(api_key, start, end):
    """Add movies to dataframe.

    Args:
        api_key: API key for OMDB
        start: starting movie ID number
        end: ending movie ID number

    Returns:
        dataframe of movies with data
    """
    start, end = validate_input(start, end)

    dataframe = get_movie_list()

    sleep_amount = 0
    if end - start > 1000:
        sleep_amount = 90

    while start <= end:
        time.sleep(sleep_amount)
        movie_string = get_imdb_string(start)
        if not dataframe['imdb_id'].str.contains(movie_string).any():
            dataframe = add_individual_movie(movie_string, dataframe, api_key)
        start += 1

    return dataframe


def create_browser_instance():
    """Create browser instance of RYM.

    Returns:
        chrome browser with RYM
    """
    # currently using Chrome Version 84
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(
        executable_path='omdb_rym/chromedriver',
        options=chrome_options,
    )
    driver.maximize_window()
    driver.get('https://rateyourmusic.com/')
    return driver


def get_search_results(browser_instance, searchterm, not_checked):
    """Search for movie in RYM.

    Args:
        browser_instance: instance of browser
        searchterm: movie to search for
        not_checked: movies in df not checked

    Returns:
        soup of search results
    """
    searchbar = browser_instance.find_element_by_name('searchterm')
    searchbar.click()
    ActionChains(browser_instance).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.DELETE).perform()
    searchbar.send_keys(not_checked['title'].iloc[searchterm])
    search_type = browser_instance.find_element_by_class_name('search_options_frame')
    ActionChains(browser_instance).move_to_element(search_type).perform()
    search_type_film = browser_instance.find_element_by_id('searchtype_F')
    ActionChains(browser_instance).click_and_hold(search_type_film).release().perform()
    search_enter = browser_instance.find_element_by_id('mainsearch_submit')
    ActionChains(browser_instance).click_and_hold(search_enter).release().perform()

    searchresults = SoupStrainer(id='searchresults')
    return BeautifulSoup(
        browser_instance.page_source,
        'lxml',
        parse_only=searchresults,
    )


def search_rym(dataframe):
    """Check if movie is on RYM.

    Args:
        dataframe: dataframe of movies to search

    Returns:
        dataframe with RYM data
    """
    scraper_sleep_time = 90

    not_checked = dataframe[(pd.isnull(dataframe.in_rym)) & (dataframe.type == 'movie')]

    driver = create_browser_instance()

    for index in enumerate(not_checked):
        soup = get_search_results(driver, index, not_checked)

        # checks if movies are in RYM database
        dataframe['in_rym'].loc[
            dataframe['imdb_id'] == not_checked['imdb_id'].iloc[index]
        ] = check_rym(
            soup,
            not_checked['title'].iloc[index],
            not_checked['year'].iloc[index],
        )

        time.sleep(scraper_sleep_time)

    driver.quit()

    dataframe.to_csv('movie_list.csv', index=False, header=True)

    return dataframe


def get_similarity_ratio(title, link):
    """Get similarity ratio between imdb and rym.

    Args:
        title: title from omdb
        link: span search from rym soup

    Returns:
        boolean indicating if there is a match
    """
    minimum_similarity_score = 0.6
    ratio = SequenceMatcher(
        None,
        link.find_previous_sibling('span').find('a').get_text(),
        title,
    ).ratio()
    return bool(ratio > minimum_similarity_score)


def check_rym(soup, title, year):
    """Search for results that match title and year in RYM soup.

    Args:
        soup: soup containing all data from search
        title: title of film
        year: year film was produced

    Returns:
        returns boolean of whether movie is in RYM
    """
    links = soup.find_all('span')
    for link in links:
        if link.find(text=re.compile('({arg})'.format(arg=str(year)))):
            with suppress(AttributeError):
                if get_similarity_ratio(title, link):
                    return True
    return False


def create_non_rym_dataframe(dataframe):
    """Create CSV file of movies on OMDb and not on RYM.

    Args:
        dataframe: dataframe of movies with omdb and rym info

    Returns:
        Dataframe of non RYM movies
    """
    return dataframe.loc[not dataframe['in_rym'], ['imdb_id', 'title', 'year']]


def main(api_key, start, end):
    """Get movies in omdb not in RYM.

    Args:
        api_key: key to use omdb api
        start: starting movie id number in imdb
        end: ending movie id number in imdb

    Returns:
        dataframe with movie info for movies not in RYM
    """
    movie_list = add_movies(api_key, start, end)
    movie_list = search_rym(movie_list)
    return create_non_rym_dataframe(movie_list)


if __name__ == '__main__':
    user_api_key = input('Enter your API key: ')
    start_point = input('Enter a start number: ')
    end_point = input('Enter an end number: ')
    movie_list = main(user_api_key, start_point, end_point)
    movie_list.to_csv('non_RYM.csv', encoding='utf-8', index=False)
