"""Retrieve films from OMDb and check which films are on RYM

Functions:

    get_movie_list()
    get_imdb_string(number)
    get_movie(imdb_id, user_api_key)
    add_movies(user_api_key, start_point, end_point)
    search_rym(dataframe)
    check_rym(soup, title, year)
    create_non_rym_dataframe(dataframe)
"""

# imports

import math
import re
import time

from difflib import SequenceMatcher

import pandas as pd
import omdb

from bs4 import BeautifulSoup, SoupStrainer
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options


def get_movie_list():
    """Read dataframe if it exists, else create new one"""
    try:
        with open("movie_list.csv", "r"):
            dataframe = pd.read_csv("movie_list.csv")
    except IOError:
        dataframe = pd.DataFrame(
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
                'in_rym'])
    return dataframe


def get_imdb_string(number):
    """Converts number to IMDB_ID String"""
    return "tt" + "0" * \
        (7 - (int(math.log10(int(number))) + 1)) + str(int(number))


def get_movie(imdb_id, api_key):
    """Get movie from imdb_id"""
    omdb.set_default("apikey", api_key)
    return omdb.imdbid(imdb_id)


def add_movies(api_key, start, end):
    """Add movies to dataframe"""
    try:
        start = int(start)
        end = int(end)
    except ValueError:
        raise SystemExit

    dataframe = get_movie_list()

    sleep_amount = 0
    if end - start > 1000:
        sleep_amount = 90

    while start <= end:
        time.sleep(sleep_amount)
        movie_string = get_imdb_string(start)
        if not dataframe["imdb_id"].str.contains(movie_string).any():
            movie_data = get_movie(movie_string, api_key)
            if not movie_data:
                print(movie_string)
                break
            dataframe = dataframe.append(movie_data, ignore_index=True)
        start += 1

    return dataframe


def search_rym(dataframe):
    """Check if movie is on RYM"""
    not_checked = dataframe[(pd.isnull(dataframe.in_rym))
                            & (dataframe.type == "movie")]

    # currently using Chrome Version 84
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(
        executable_path="omdb_rym/chromedriver",
        options=chrome_options)
    driver.maximize_window()
    driver.get("https://rateyourmusic.com/")

    for index in range(len(not_checked)):
        searchbar = driver.find_element_by_name("searchterm")
        searchbar.click()
        ActionChains(driver).key_down(
            Keys.CONTROL).send_keys('a').key_up(
                Keys.CONTROL).send_keys(
                    Keys.DELETE).perform()
        searchbar.send_keys(not_checked["title"].iloc[index])
        search_type = driver.find_element_by_class_name("search_options_frame")
        ActionChains(driver).move_to_element(search_type).perform()
        search_type_film = driver.find_element_by_id("searchtype_F")
        ActionChains(driver).click_and_hold(
            search_type_film).release().perform()
        search_enter = driver.find_element_by_id("mainsearch_submit")
        ActionChains(driver).click_and_hold(search_enter).release().perform()

        searchresults = SoupStrainer(id="searchresults")
        soup = BeautifulSoup(
            driver.page_source,
            "lxml",
            parse_only=searchresults)

        # checks if movies are in RYM database
        if check_rym(
                soup,
                not_checked["title"].iloc[index],
                not_checked["year"].iloc[index]):
            dataframe["in_rym"].loc[dataframe["imdb_id"] ==
                                    not_checked["imdb_id"].iloc[index]] = True
        else:
            dataframe["in_rym"].loc[dataframe["imdb_id"] ==
                                    not_checked["imdb_id"].iloc[index]] = False

        time.sleep(90)

    driver.quit()

    del not_checked

    dataframe.to_csv(r"movie_list.csv", index=False, header=True)

    return dataframe


def check_rym(soup, title, year):
    """Searches for results that match title and year in RYM soup"""
    links = soup.find_all("span")
    for link in links:
        if link.find(text=re.compile("(" + str(year) + ")")):
            try:
                ratio = SequenceMatcher(None, link.find_previous_sibling(
                    "span").find("a").get_text(), title).ratio()
                if ratio > 0.6:
                    return True
            except AttributeError:
                continue
    return False


def create_non_rym_dataframe(dataframe):
    """Creates CSV file of movies on OMDb and not on RYM"""
    return dataframe.loc[not dataframe['in_rym'], ['imdb_id', 'title', 'year']]


def main(api_key, start, end):
    """Main part of program"""
    movie_list = add_movies(api_key, start, end)
    movie_list = search_rym(movie_list)
    movie_list = create_non_rym_dataframe(movie_list)
    movie_list.to_csv('non_RYM.csv', encoding='utf-8', index=False)


if __name__ == "__main__":
    user_api_key = input("Enter your API key: ")
    start_point = input("Enter a start number: ")
    end_point = input("Enter an end number: ")
    main(user_api_key, start_point, end_point)
