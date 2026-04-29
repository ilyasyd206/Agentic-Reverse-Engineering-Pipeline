import os
import stat


def remove_readonly(func, path, _):
    """
    Pomocná funkcia pre Windows na mazanie read-only súborov.
    Použitie: shutil.rmtree(path, onerror=remove_readonly)
    """
    os.chmod(path, stat.S_IWRITE)
    try:
        func(path)
    except Exception:
        pass