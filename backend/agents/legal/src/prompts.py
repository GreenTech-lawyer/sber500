from jinja2 import Template


PROMPTS = {
    'legal_review': Template('''Роль: Юрист.
    Вам дан документ: {{ snippet }}
    Дайте краткий обзор: ключевые положения, риски, и рекомендации (не более 300 слов).'''),
    'contract_summary': Template('''Роль: Юрист — контракт-аналитик.
    Дайте пунтктуационный список ключевых обязательств и сроков из документа: {{ snippet }}''')
}


def render(prompt_name: str, **kwargs) -> str:
    return PROMPTS[prompt_name].render(**kwargs)
