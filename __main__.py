from Scraper import Scraper
import json

pretty_print = lambda x: print(json.dumps(x, indent=2))

scraper = Scraper(username='iroy@ucsd.edu', password="05ASDFghjkl;'")
scraper.get_courses(dump_json=True)