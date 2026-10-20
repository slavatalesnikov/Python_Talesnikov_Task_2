"""общий формат XML для клиента, сервера и примеров запросов."""

from xml.etree import ElementTree as element_tree


def fill(element, value):
    """записывает словарь, список, число, строку или null в XML.

    атрибут nil отличает отсутствие результата от пустой строки.
    ElementTree экранирует специальные символы текста автоматически.
    """
    if value is None:
        element.set('nil', 'true')
    elif isinstance(value, dict):
        element.set('kind', 'object')
        for key, child in value.items():
            fill(element_tree.SubElement(element, key), child)
    elif isinstance(value, list):
        element.set('kind', 'list')
        for child in value:
            fill(element_tree.SubElement(element, 'item'), child)
    else:
        element.set('type', 'int' if isinstance(value, int) else 'str')
        element.text = str(value)


def dumps(value, root='response'):
    """возвращает UTF-8 XML с декларацией кодировки."""
    element = element_tree.Element(root)
    fill(element, value)
    return element_tree.tostring(element, encoding='utf-8',
                                 xml_declaration=True)


def read(element):
    """восстанавливает значения, включая пустые списки и строки."""
    if element.get('nil') == 'true':
        return None
    if element.get('kind') == 'list':
        return [read(child) for child in element]
    if element.get('kind') == 'object' or len(element):
        return {child.tag: read(child) for child in element}
    if element.get('type') == 'int':
        return int(element.text or '')
    return element.text or ''


def loads(data):
    """разбирает ответ API или XML-тело запроса."""
    try:
        return read(element_tree.fromstring(data))
    except element_tree.ParseError as error:
        raise ValueError('некорректный XML') from error


def fields(data):
    """принимает плоское XML-тело с полями, например <request/>."""
    value = loads(data)
    if value == '':
        return {}
    if not isinstance(value, dict):
        raise ValueError('ожидается XML с полями')
    if any(isinstance(item, (dict, list)) for item in value.values()):
        raise ValueError('поля должны быть простыми значениями')
    return value
