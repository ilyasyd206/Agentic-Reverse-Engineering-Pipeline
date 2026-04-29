import os

# Absolútna cesta k DB — funguje bez ohľadu na pracovný adresár
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "db")