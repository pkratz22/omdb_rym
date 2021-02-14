"""Test omdb_rym functions.

Classes:

    TestOmdbRym

Functions:

    test_get_imdb_string(self)
    test_get_movie(self)
    test_add_movies(self)
"""

import unittest

import omdb_rym


class TestOmdbRym(unittest.TestCase):
    """Test cases for omdb_rym."""

    def test_get_imdb_string(self):
        """Test getting IMDb ID for movie from integer."""
        # one digit input
        self.assertEqual(omdb_rym.get_imdb_string(5), 'tt0000005')

        # two digit input
        self.asomdbsertEqual(omdb_rym.get_imdb_string(55), 'tt0000055')

        # three digit input
        self.assertEqual(omdb_rym.get_imdb_string(555), 'tt0000555')

        # four digit input
        self.assertEqual(omdb_rym.get_imdb_string(5555), 'tt0005555')

        # five digit input
        self.assertEqual(omdb_rym.get_imdb_string(55555), 'tt0055555')

        # six digit input
        self.assertEqual(omdb_rym.get_imdb_string(555555), 'tt0555555')

        # seven digit input
        self.assertEqual(omdb_rym.get_imdb_string(5555555), 'tt5555555')

        # eight digit input
        self.assertEqual(omdb_rym.get_imdb_string(55555555), 'tt55555555')

        # string input
        self.assertEqual(omdb_rym.get_imdb_string('5'), 'tt0000005')

    def test_get_movie(self):
        """Test getting movie from IMDb ID."""
        user_api_key = input('Enter your API key: ')

        # correct input
        self.assertIsNotNone(omdb_rym.get_movie('tt55555555', user_api_key))

        # flawed input
        self.assertIsNotNone(omdb_rym.get_movie(5, user_api_key))

    def test_add_movies(self):
        """Test adding movie between start and end points."""
        user_api_key = input('Enter your API key: ')
        # start point < end point
        self.assertIsNotNone(omdb_rym.add_movies(user_api_key, 1, 2))

        # start point == end point
        self.assertIsNotNone(omdb_rym.add_movies(user_api_key, 6, 6))

        # start point > end point
        self.assertIsNotNone(omdb_rym.add_movies(user_api_key, 9, 8))

        with self.assertRaises(SystemExit):
            # blank start point
            omdb_rym.add_movies(user_api_key, '', 2)
            # blank end point
            omdb_rym.add_movies(user_api_key, 2, '')
            # blank start and end points
            omdb_rym.add_movies(user_api_key, '', '')


if __name__ == '__main__':
    unittest.main()
