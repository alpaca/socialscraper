import unittest, os
from ...facebook import FacebookScraper

import pprint
pp = pprint.PrettyPrinter(indent=4)

import logging
logging.basicConfig(level=logging.INFO)

class TestFacebookScraper(unittest.TestCase):

    def setUp(self):
        self.email = os.getenv("FACEBOOK_EMAIL")
        self.username = os.getenv("FACEBOOK_USERNAME")
        self.password = os.getenv("FACEBOOK_PASSWORD")

        self.test_username = "sabina.shamayeva" # sabina.shamayeva
        self.test_pagename = "mightynest"

        self.scraper = FacebookScraper()
        self.scraper.add_user(email=self.email, password=self.password)
        self.scraper.login()

    def test_graph_search(self):

        def test_pages_liked(username):
            for item in self.scraper.graph_search(username, "pages-liked"):
                print item
            self.assertEqual(True,True)

        def test_likers(pagename):
            for item in self.scraper.graph_search(pagename, "likers"):
                print item
            self.assertEqual(True,True)

        def test_about(username):
            stuff = self.scraper.get_about(username)
            pp.pprint(stuff)
            self.assertEqual(True,True)

        def test_timeline(username):
            from ...facebook import timeline
            timeline.search(self.scraper.browser, self.scraper.cur_user, username)

        # test_about(self.test_username)
        # test_timeline(self.test_username)
        test_pages_liked(self.test_username)

        # takes too long
        # test_about(self.test_pagename) # not fully supported yet
        # test_timeline(self.test_pagename)
        # test_likers(self.test_pagename)

if __name__ == "__main__":
    unittest.main()