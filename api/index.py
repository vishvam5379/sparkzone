import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sparkzoneproject.wsgi import application

app = application
