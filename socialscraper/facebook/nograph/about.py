# -*- coding: utf-8 -*-

import logging, lxml.html
from dateutil import parser

from .. import public
from ..models import FacebookUser
from ...base import ScrapingError

logger = logging.getLogger(__name__)

ABOUT_URL = "https://www.facebook.com/%s/info"

def get_about(browser, current_user, graph_name, graph_id=None, api=None):

    # shit gets weird when graph_name == current_user.username
    if current_user.username == graph_name:
        raise ScrapingError("don't scrape yourself plz")

    ret = {
        "family": {},
        "experiences": {},
        "relationships": {},
        "places": {},
        "contact": {},
        "basic": {},
        "about": [],
        "quotes": [],
        "event": {}
    }

    def get_text(element_list):
        if element_list: return element_list[0].text_content()

    def get_previous(element_list):
        if element_list: return [element_list[0].getprevious()]

    def get_rows(data):
        for table in data.cssselect('tbody'): 
            for row in table.cssselect('tr'): 
                yield row

    def get_cells(data):
        for table in data.cssselect('tbody'): 
            for row in table.cssselect('tr'): 
                for cell in row.cssselect('td'):
                    yield cell

    def parse_experience(cell):
        for experience in cell.cssselect(".experienceContent"):
            experience_title = get_text(experience.cssselect(".experienceTitle"))
            # experience_title_url = experience.cssselect(".experienceTitle")[0]
            experience_body = get_text(experience.cssselect(".experienceBody"))
            yield experience_title, experience_body

    def parse_generic_cell(cell):
        previous_cell = get_previous(cell.cssselect('.aboutSubtitle'))
        if previous_cell and previous_cell[0].cssselect('a'):
            name_url = previous_cell[0].cssselect('a')[0].get('href')
        else:
            name_url = None

        name = get_text(previous_cell)
        content = get_text(cell.cssselect('.aboutSubtitle'))
        print name_url
        return name, content
        # return (name, name_url), content

    def parse_generic_row(row):
        name = get_text(row.cssselect('th'))
        content = get_text(row.cssselect('td'))
        return name, content

    response = browser.get(ABOUT_URL % graph_name)
    for element in lxml.html.fromstring(response.text).cssselect(".hidden_elem"): 
        comment = element.xpath("comment()")
        if not comment: continue
        
        element_from_comment = lxml.html.tostring(comment[0])[5:-4]
        doc = lxml.html.fromstring(element_from_comment)
        fbTimelineSection = doc.cssselect('.fbTimelineSection.fbTimelineCompactSection')
        fbTimelineFamilyGrid = doc.cssselect('.fbTimelineFamilyGrid')
        fbTimelineAboutMeHeader = doc.cssselect('.fbTimelineAboutMeHeader')

        # this is for scraping a Page
        if fbTimelineAboutMeHeader:
          title = get_text(fbTimelineAboutMeHeader[0].cssselect('.uiHeaderTitle'))
          # print title

          if "About" in title:
            pass
              # print doc.text_content() 
          elif "Basic Info" in title:
            pass
              # print doc.text_content()

        if fbTimelineFamilyGrid:
            familyList = fbTimelineFamilyGrid[0].cssselect('.familyList')[0]
            for member in familyList:
                name, status = parse_generic_cell(member)
                ret['family'][status] = name

                # FacebookFamily(profile_id=, relationship=status, uid=, name=name)

        if fbTimelineSection:
            title = get_text(fbTimelineSection[0].cssselect('.uiHeaderTitle'))
            data = fbTimelineSection[0].cssselect('.profileInfoTable') if fbTimelineSection else None

            if not title or not data: continue
            
            # experiences_keys = ['College', 'Employers', 'High School']
            if "Work and Education" in title:
                for row in get_rows(data[0]):
                    if not row.cssselect('th'): continue
                    header = row.cssselect('th')[0].text_content() 
                    ret['experiences'][header] = {}
                    for cell in row.cssselect('td'): 
                        for experienceTitle, experienceBody in parse_experience(cell): 
                            ret['experiences'][header][experienceTitle] = experienceBody

            # relationships_keys = ['In a relationship']
            elif "Relationship" in title:
                for cell in get_cells(data[0]): 
                    name, status = parse_generic_cell(cell)
                    ret['relationships'][status] = name

            # places_keys = ['Current City', 'Hometown']
            elif "Places Lived" in title:
                for cell in get_cells(data[0]): 
                    name, status = parse_generic_cell(cell)
                    ret['places'][status] = name

            # contact_keys = ['Address', 'Email', 'Mobile Phones']
            elif "Contact Information" in title:
                for row in get_rows(data[0]): 
                    name, status = parse_generic_row(row)
                    ret['contact'][name] = status

            # basic_keys = ['Birthday', 'Gender', 'Interested In', 'Languages', 'Political Views', 'Relationship Status']
            elif "Basic Information" in title:
                for row in get_rows(data[0]): 
                    name, status = parse_generic_row(row)
                    ret['basic'][name] = status

            # about_keys = None
            elif "About" in title:
                data = fbTimelineSection[0].getchildren()[1]
                for quote in data.cssselect('.profileText'): 
                    ret['about'].append(quote.text_content())

            # quotes_keys = None
            elif "Favorite Quotations" in title:
                data = fbTimelineSection[0].getchildren()[1]
                for quote in data.cssselect('.profileText'):
                    ret['quotes'].append(quote.text_content())

            # family_keys = ['Brother']
            elif "Family" in title: # empty
                pass # this will be empty Family information above in 'fbTimelineFamilyGrid'

            # events_keys = None
            elif "Life Events" in title:
                # TODO: parse life events
                data = fbTimelineSection[0].getchildren()[1].text_content()
                pass
            elif "Pages" in title:
                pass
                # TODO: parse pages admined/owned by user
            elif 'Favorites' in title:
                pass
            else:
                raise ScrapingError("Unrecognized fbTimelineSection %s" % title)

    if not graph_id: graph_id = public.get_id(graph_name)
    
    birthday = ret['basic'].get('Birthday', None)
    birthday = parser.parse(birthday) if birthday else None
    sex = ret['basic'].get('Gender', None)
    email = ret['contact'].get('Email', None)
    college = ret['experiences'].get('College', None)
    employer = ret['experiences'].get('Employers', None)
    highschool = ret['experiences'].get('High School', None)
    currentcity = ret['places'].get('Current City', None)
    hometown = ret['places'].get('Hometown', None)

    sex = sex.lower() if sex else None
    
    email = email if email and not "Ask for" in email else None
    college = unicode(college) if college is not None else None
    employer = unicode(employer) if employer is not None else None
    highschool = unicode(highschool) if highschool is not None else None
    currentcity = unicode(currentcity) if currentcity is not None else None
    hometown = unicode(hometown) if hometown is not None else None

    user = FacebookUser(
        uid=graph_id, 
        username=graph_name, 
        email=email, 
        birthday=birthday, 
        sex=sex, 
        college=college, 
        employer=employer,
        highschool=highschool,
        currentcity=currentcity,
        hometown=hometown
    )

    print ret
    
    return user