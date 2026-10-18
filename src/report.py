"""формула 24: отбор Feedback, левое соединение и проекция."""

from src.schema import REPORT_SECONDS


def build_report(tables, now):
    """сохраняет каждое Assignment даже без подходящего Feedback.

    фильтр created > now - 300 относится только к Feedback до соединения.
    после проекции одинаковые тройки удаляются, как в алгебре отношений.
    """
    boundary = now - REPORT_SECONDS
    recent = [row for row in tables['feedback'] if row['created'] > boundary]
    triples = set()
    for assignment in tables['assignment']:
        matches = [row for row in recent
                   if row['assignment'] == assignment['identifier']]
        if matches:
            for feedback in matches:
                triples.add((assignment['parameter'], feedback['cache_hit'],
                             feedback['output']))
        else:
            triples.add((assignment['parameter'], None, None))
    return [{'parameter': parameter, 'cache_hit': cache_hit, 'output': output}
            for parameter, cache_hit, output in sorted(triples, key=repr)]
