from .base import BaseScraper, UsageError, ScrapingError
import lxml, re, json, urllib

class FacebookScraper(BaseScraper):
    class UserAccount(BaseScraper.UserAccount):
        def __init__(self,email,password):
            BaseScraper.UserAccount.__init__(self, email, password)
            self.email = email
            self.id = None
            self.username = None

    def __init__(self,user_agents = None):
        """Initialize the Facebook scraper."""
        BaseScraper.__init__(self,user_agents)
        return

    def login(self):
        """Log in to Facebook."""
        user_acct = self.pick_random_user()
        self.cur_user = user_acct

        self._browser.select_form(nr=1)
        self._browser.form["email"] = user_acct.email
        self._browser.form["pass"] = user_acct.password
        resp = self._browser.submit()
        if "recognize your email address or phone number." not in resp.read():
            raise UsageError("Username or Password incorrect.")

        self._browser.select_form(nr=0)
        self._browser.submit()
        # clicked continue

        resp = self._browser.response()
        if "checkpoint" in resp.geturl():
            self._browser.select_form(nr=0)
            self._browser.submit()
            # "this was me."
            resp = self._browser.response()

        assert ("home.php" in resp.geturl()) or \
               ("findfriends" in resp.geturl()) or \
               ("phoneacquire" in resp.geturl())

        base_url = 'https://m.facebook.com/profile.php'
        resp = self._browser.open(base_url)
        doc = lxml.html.fromstring(resp.read())

        profile_url = filter(lambda x: 
            x.text_content() == 'About', 
            doc.cssselect('.sec'))[0].get('href')

        self.cur_user.username = re.sub('\?.*', '', profile_url[1:])
        self.cur_user.id = self.get_graph_id(self.cur_user.username)

    def get_graph_id(self, graph_name):
        """Get the graph ID given a name."""
        resp = self._browser.open('https://graph.facebook.com/' + graph_name)
        return json.loads(resp.read())['id']

    def get_graph_name(self, graph_id):
        """Get the graph name given a graph ID."""
        resp = self._browser.open('https://graph.facebook.com/' + graph_id)
        return json.loads(resp.read())['name']

    def graph_search(self, graph_id, method_name, post_data = None):
        """Graph search."""
        # initial request
        if not post_data:
            base_url = "https://www.facebook.com/search/%s/%s" % (graph_id,
                                                                  method_name)
            resp = self._browser.open(base_url)
            raw_html = resp.read()
            raw_json = self._find_script_tag_with_post_data(raw_html)
            if not raw_json:
                raise ScrapingError

        else:
            parameters = {  'data': json.dumps(post_data), 
                            '__user': self.cur_user.id, 
                            '__a': 1, 
                            '__req': 'a', 
                            '__dyn': '7n8apij35CCzpQ9UmWOGUGy1m9ACwKyaF3pqzAQ',
                            '__rev': 1106672 }

            base_url = "https://www.facebook.com/ajax/pagelet/\
            generic.php/BrowseScrollingSetPagelet?%s" % urllib.urlencode(parameters)
            resp = self._browser.open(base_url)
            resp_json = json.loads(resp.read()[9:])
            raw_json = resp_json['jsmods']
            raw_html = resp_json['payload']


        post_data = self.parse_post_data(raw_json)
        current_results = self.parse_result(raw_html)

        return post_data, current_results

        def parse_post_data(self, raw_json):
            """Parse post data."""

            require = raw_json['require']
            data_parameter = map(lambda x: x[3][1], filter(lambda x: 
                                    x[0] == "BrowseScrollingPager" and 
                                    x[1] == "init", 
                                    require))
            cursor_parameter = map(lambda x: x[3][0], filter(lambda x: 
                                    x[0] == "BrowseScrollingPager" and 
                                    x[1] == "pageletComplete", 
                                    require))

            data_parameter = filter(None, data_parameter)
            cursor_parameter = filter(None, cursor_parameter)

            if data_parameter and cursor_parameter: 
                return dict(data_parameter[0].items() + 
                            cursor_parameter[0].items())
            elif data_parameter:
                return dict(data_parameter[0].items())
            elif cursor_parameter:
                return dict(cursor_parameter[0].items())
            return None

    def find_script_tag_with_post_data(self, raw_html):
        doc = lxml.html.fromstring(raw_html)
        script_tag = filter(lambda x: x.text_content().find('cursor') != -1, 
                            doc.cssselect('script'))
        if not script_tag: 
            return None
        return json.loads(script_tag[0].text_content()[35:-2])

    def parse_result(self, raw_html):
        doc = lxml.html.fromstring(raw_html)
        return map(lambda x: (x.get('href'), x.text_content()) , 
                            doc.cssselect('div[data-bt*=title] a'))

    def graph_loop(self,graph_name,method_name,callback):
        graph_id = self.get_graph_id(graph_name)
        post_data, cur_results = self.graph_search(graph_id, method_name)
        if not (post_data and cur_results):
            raise ScrapingError
        callback(cur_results,graph_name,method_name)

        while post_data:
            cur_post_data, cur_results = self.graph_search(graph_id, 
                                                           method_name, 
                                                           post_data)
            if not (post_data and cur_results):
                break
            callback(cur_results, graph_name, method_name)
            post_data.update(cur_post_data)
        return


    def add_user_info(self,email,password):
        """Set the account information to use when a login is required.
        Overrides BaseScraper.add_user_info
        """
        self.users.append(FacebookScraper.UserAccount(email,password))
        return