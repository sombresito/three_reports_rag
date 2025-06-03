def chunk_report(report):
    """
    report: list — массив тест-кейсов (реальный Allure отчет)
    """
    chunks = []
    team_names = set()
    for case in report:
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
        # Название команды ищем в labels
        for lbl in chunk["labels"]:
            if lbl.get("name") == "suite":
                team_names.add(lbl.get("value"))
        chunks.append(chunk)
    # Название команды — если одинаковое, то берём одно, иначе склеиваем
    if len(team_names) == 1:
        team_name = next(iter(team_names))
    else:
        team_name = "_".join(sorted(team_names))
    return chunks, team_name
