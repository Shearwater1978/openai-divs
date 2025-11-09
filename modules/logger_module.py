import logging

def get_logger(name: str) -> logging.Logger:
    # Create or get a named logger with a simple console handler.
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger
