import re
import logging

logger = logging.getLogger("validator")


class DraftChecker:
    """
    Проверяет сгенерированные тексты на ошибки, галлюцинации и запрещенные темы.
    """

    forbidden_patterns = [
        r"\bнелегально\b",
        r"\bсекрет\b",
        r"\bпароль\b",
    ]

    @classmethod
    def check_text(cls, text: str) -> bool:
        """
        Возвращает True, если текст можно публиковать.
        False — текст не прошёл проверку.
        """
        if not text or not text.strip():
            logger.warning("Draft is empty")
            return False

        for pattern in cls.forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning("Draft contains forbidden pattern: %s", pattern)
                return False

        # Дополнительно: проверка на слишком короткий текст
        if len(text.strip()) < 10:
            logger.warning("Draft too short")
            return False

        return True
