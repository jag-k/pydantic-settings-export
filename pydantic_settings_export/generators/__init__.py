from .abstract import AbstractGenerator
from .dotenv import *
from .markdown import *
from .simple import *
from .toml import *

Generators = AbstractGenerator.create_generator_config_model()
