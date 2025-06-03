def chunk_report(report: dict):
    """Разбивает отчёт на чанки по тест-кейсам и возвращает название команды."""
    chunks = []
    team_name = None
    for suite in report.get('children', []):
        for case in suite.get('children', []):
            chunk = {
                "name": case.get("name"),
                "status": case.get("status"),
                "uid": case.get("uid"),
                "duration": case.get("time", {}).get("duration"),
                "labels": case.get("labels", []),
                "description": case.get("description"),
                "steps": case.get("steps"),
                "attachments": case.get("attachments"),
                "flaky": case.get("flaky", False),
                "statusMessage": case.get("statusMessage"),
                "statusTrace": case.get("statusTrace"),
            }
            # Название команды берем из labels
            if not team_name:
                for lbl in chunk["labels"]:
                    if lbl.get("name") == "suite":
                        team_name = lbl.get("value")
            chunks.append(chunk)
    if not team_name:
        team_name = "default_team"
    return chunks, team_name
