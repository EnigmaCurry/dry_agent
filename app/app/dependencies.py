import os
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=os.path.abspath("app/templates"))
