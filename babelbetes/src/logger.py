# File: logger.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import logging

class Logger:
    @staticmethod
    def get_logger(name: str, level=logging.DEBUG) -> logging.Logger:
        """
        Returns a configured logger instance with the specified name and log level.

        Args:
            name (str): The name of the logger.
            level (int): The logging level (e.g., logging.INFO, logging.DEBUG).

        Returns:
            logging.Logger: Configured logger.
        """
        logger = logging.getLogger(name)

        # Avoid adding handlers if the logger is already configured
        if not logger.handlers:
            logger.setLevel(level)

            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)

            # Add color formatter
            console_handler.setFormatter(ColorFormatter('%(asctime)s %(message)s', datefmt='[%H:%M:%S]'))
            
            # Add the handler to the logger
            logger.addHandler(console_handler)
            logger.propagate = False

        return logger

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",  # White
        logging.INFO: "\033[32m",   # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",    # Red
        logging.CRITICAL: "\033[41m", # Red background
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, self.RESET)
        record.msg = f"{log_color}{record.msg}{self.RESET}"
        return super().format(record)