from .abstract import *
from .dotenv import *
from .markdown import *


ALL_GENERATORS: list[type[AbstractGenerator]] = [DotEnvGenerator, MarkdownGenerator]
