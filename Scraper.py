import json
import requests
from bs4 import BeautifulSoup

class Scraper():
    BASE_URL = "https://www.gradescope.com"
    USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/77.0.3865.120 Safari/537.36")

    COURSES_PATH = "data/courses.json"
    TERM_FORMAT = {"20": "", "Fall ": "FA", "Winter ": "WI", "Spring ": "SP"}

    def __init__(self, username, password, terms=[]):
        self.session = self.get_session(username, password)
        self.terms = terms or self.get_terms()

    def get_session(self, username, password):
        session = requests.Session()
        response = session.get(self.BASE_URL)
        soup = BeautifulSoup(response.content, "html.parser")
        authenticity_token = soup.find("input", {"name": "authenticity_token"}).get("value")

        login_data = {
            "utf8": "✓",
            "authenticity_token": authenticity_token,
            "session[email]": username,
            "session[password]": password,
            "session[remember_me]": "0,1",
            "commit": "Log+In",
            "session[remember_me_sso]": "0",
        }

        headers = {
            "User-Agent": self.USER_AGENT,
            "Referer": self.BASE_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        res = session.post(f"{self.BASE_URL}/login", data=login_data, headers=headers)
        if res.status_code in [200, 302]: return session

    def get_soup(self, endpoint):
        res = self.session.get(f"{self.BASE_URL}/{endpoint}")
        if res.status_code not in [200, 302]: 
            raise Exception(f"Error {res.status_code}")
        else: 
            return BeautifulSoup(res.content.decode(), features="html.parser")

    def format_term(self, term):
        for old, new in self.TERM_FORMAT.items():
            term = term.replace(old, new)
        return term

    def get_terms(self):
        soup = self.get_soup("account")
        terms = soup.find_all("div", {"class": "courseList--term"})
        return [self.format_term(term.text) for term in terms]
    
    def get_assignment_info(self, row):
        btn = row.find("button")
        anchor = row.find("a")

        if btn: assignment = {"name": btn.text, "id": btn.get("data-assignment-id")}
        elif anchor: assignment = {"name": anchor.text, "id": anchor.get("href").split("/")[3]}
        else: assignment = {"name": row.find("th").text}

        score = row.find("div", {"class": "submissionStatus--score"})
        if score: assignment.update({"submission-status": "Graded", "score": score.text})
        elif row.find(string="Submitted"): assignment["submission-status"] = "Submitted"
        elif row.find(string="No Submission"): assignment["submission-status"] = "No Submission"

        times = row.find_all("time")
        if times:
            assignment["start-datetime"] = times[0].get("datetime")
            assignment["end-datetime"] = times[1].get("datetime")
        
        return assignment

    def get_assignments(self, course_id):
        soup = self.get_soup(f"courses/{course_id}")
        rows = soup.find("tbody").find_all("tr", {"role": "row"})
        return [self.get_assignment_info(row) for row in rows]
    
    def get_course_info(self, course_id, with_assignments=False):
        soup = self.get_soup(f"courses/{course_id}")
        header_element = soup.find("header", {"class": "courseHeader"})

        if header_element:
            course_name = header_element.find("h1").text.replace(" ", "")
            course_term = header_element.find("h2", {"class": "courseHeader--term"}).text
            course_term = self.format_term(course_term)

            course_info = {"name": course_name, "term": course_term, "id": course_id}
            if with_assignments:
                course_info["assignments"] = self.get_assignments(course_id)
            return course_info

    def get_courses(self, with_assignments=True, dump_json=False):
        soup = self.get_soup("account")
        hrefs = list(filter(lambda x: x, map(
            lambda a: a.get("href"),
            soup.find_all("a", {"class": "courseBox"})
        )))

        courses = [self.get_course_info(href.split("/")[-1], with_assignments) for href in hrefs]
        courses = [course for course in courses if course['term'] in self.terms]
        if dump_json:
            with open(self.COURSES_PATH, "w") as f:
                json.dump(courses, f, indent=2)
        return courses