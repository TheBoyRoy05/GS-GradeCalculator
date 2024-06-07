import re
import json
from bs4 import BeautifulSoup
from gradescope import api

class GSCalculator():

    ASSIGNMENT_URL_PATTERN = r"/courses/([0-9]*)/assignments/([0-9]*)/submissions/([0-9]*)$"

    def __init__(self, terms=[], use_json=False, json_path="grading-schema.json"):
        self.terms = terms if len(terms) > 0 else self.get_terms()
        self.use_json = use_json
        self.json_path = json_path

    def format_term(self, term):
        term = term.replace("20", "")
        term = term.replace("Fall ", "FA")
        term = term.replace("Winter ", "WI")
        term = term.replace("Spring ", "SP")
        return term

    def get_terms(self):
        result = api.request(endpoint="account")
        soup = BeautifulSoup(result.content.decode(), features="html.parser")
        terms = soup.find_all("div", {"class": "courseList--term"})
        return list(map(lambda term: self.format_term(term.text), terms))

    def get_courses(self):
        if self.use_json:
            return self.load_json(self.json_path)

        response = api.request(endpoint="account")
        soup = BeautifulSoup(response.content, features="html.parser")
        hrefs = list(filter(lambda s: s, map(
            lambda anchor: anchor.get("href"),
            soup.find_all("a", {"class": "courseBox"})
        )))
        course_ids = list(map(lambda href: href.split("/")[-1], hrefs))
        courses = [self.get_course_info(id) for id in course_ids]
        return list(filter(lambda course: course is not None, courses))

    def get_course_info(self, course_id):
        if self.use_json:
            courses = self.load_json(self.json_path)
            for course in courses:
                if course["id"] == course_id and course_term in self.terms:
                    return {"name": course["name"], "term": course["term"], "id": course_id}
            return "Course Not Found"

        result = api.request(endpoint="courses/{}".format(course_id))
        soup = BeautifulSoup(result.content.decode(), features="html.parser")
        header_element = soup.find("header", {"class": "courseHeader"})
        if header_element:
            course_name = header_element.find("h1").text.replace(" ", "")
            course_term = header_element.find("h2", {"class": "courseHeader--term"}).text
            course_term = self.format_term(course_term)
            if course_term in self.terms:
                return {"name": course_name, "term": course_term, "id": course_id}
        else: 
            return "Course Not Found"

    def get_course_id(self, course_name, course_term):
        courses = self.get_courses()
        for course in courses:
            if course["name"].count(course_name) > 0 and course["term"] == course_term:
                return course["id"]
        return "Course Not Found"

    def get_course_assignments(self, course_id):
        result = api.request(endpoint="courses/{}".format(course_id))
        soup = BeautifulSoup(result.content.decode(), features="html.parser")

        assignment_table = soup.find("table", {"class": "table"})
        if assignment_table is None:
            return "Course Not Found"

        assignment_rows = assignment_table.findChildren("tr", {"role": "row"})
        
        assignments = []
        for row in assignment_rows:
            anchors = row.find_all("a")
            assignment = None

            for anchor in anchors:
                url = anchor.get("href")
                if url is None or url == "":
                    continue

                match = re.match(self.ASSIGNMENT_URL_PATTERN, url)
                if match is None:
                    continue

                assignment = {
                    "id": match.group(2),
                    "name": anchor.text
                }
            
            if assignment == None:
                continue

            score = row.find("div", {"class": "submissionStatus--score"})
            if score:
                assignment["submission-status"] = "Graded"
                assignment["score"] = score.text
            elif row.find(string="Submitted"):
                assignment["submission-status"] = "Submitted"
            elif row.find(string="No Submission"):
                assignment["submission-status"] = "Not Submitted"

            assignments.append(assignment)

        return assignments

    def calculate_grade(self, course_id, weights):
        assignments = self.get_course_assignments(course_id)
        grade = 0
        total_weight = 0

        for category, weight in weights.items():
            total_points = 0
            total_points_possible = 0

            for assignment in assignments:
                if "score" in assignment.keys() and assignment["name"].count(category) > 0:
                    score = assignment["score"].split(' / ')
                    total_points += score[0]
                    total_points_possible += score[1]

            if total_points_possible != 0:
                total_weight += weight
                grade += weight * total_points / total_points_possible

        return grade / total_weight
    
    def generate_json(self):
        courses = self.get_courses()
        for course in courses:
            course["categories"] = [
                {
                    "category": category,
                    "weight": 0,
                    "numDropLowest": 0, 
                    "redemptionPolicy": False,
                    "contains": category,
                    "pattern": None
                } for category in ["Homework", "Midterm", "Final"]]
            course["assignments"] = self.get_course_assignments(course["id"])

        with open(self.json_path, "w") as file:
            json.dump(courses, file, indent=4)

    def load_json(self, path):
        try:
            with open(path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print("The file was not found")
        except json.JSONDecodeError:
            print("The file is not a valid JSON")