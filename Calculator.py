import json

class Calculator:
    def __init__(self, data_path="data/courses.json"):
        self.courses = self.load_json(data_path)
        
    def load_json(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"{path} was not found")
        except json.JSONDecodeError:
            print(f"{path} is not a valid JSON")