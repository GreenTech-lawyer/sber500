from pydantic import BaseModel


class DialogueMessage(BaseModel):
    user_id: str
    text: str
    metadata: dict | None = None


class AssistantFormatter:
    """Этот класс превращает сырые данные анализа в человеческий текст."""

    @staticmethod
    def format_analysis(analysis_text: str) -> str:
        """Превращает вывод LegalAgent в понятный, мягкий, дружелюбный ответ."""
        return (
            "Вот что удалось выяснить:\n\n"
            f"{analysis_text}\n\n"
            "Если хотите — могу объяснить подробнее или сформировать итоговый вывод."
        )

    @staticmethod
    def format_user_message(message: str) -> str:
        """Просто прокидывает пользовательское сообщение — если оно является триггером для чата."""
        return f"Вы написали: {message}"
