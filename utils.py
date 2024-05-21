import logging

def setup_logging(level, log_to_file, log_to_console):
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=getattr(logging, level.upper()),
                        format=log_format,
                        handlers=[])
    if log_to_file:
        file_handler = logging.FileHandler('bot.log')
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(console_handler)
