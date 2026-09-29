import argparse
import json
import sys
from string import Template
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def build_url(base_url, path):
    raw_path = str(path)
    encoded_path = quote(raw_path, safe="/")
    return base_url.rstrip("/") + "/" + encoded_path.lstrip("/")


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def render(value, variables):
    if isinstance(value, str):
        if value.startswith("$") and value[1:] in variables and len(value.split()) == 1:
            return variables[value[1:]]
        text_variables = {key: str(item) for key, item in variables.items()}
        return Template(value).safe_substitute(text_variables)
    if isinstance(value, list):
        return [render(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: render(item, variables) for key, item in value.items()}
    return value


def call_api(base_url, step, variables):
    method = step.get("method", "GET").upper()
    path = str(render(step["path"], variables))
    url = build_url(base_url, path)

    headers = {
        "Accept": "application/json",
        **render(step.get("headers", {}), variables),
    }

    body = step.get("body")
    data = None
    rendered_body = None
    if body is not None:
        rendered_body = render(body, variables)
        data = json.dumps(rendered_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    # Debug: print and log the request body being sent
    if rendered_body is not None:
        try:
            pretty = json.dumps(rendered_body, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            pretty = str(rendered_body)
        print("Request body:", pretty)
        with open("run.log", "a", encoding="utf-8") as log:
            log.write("Request body:\n")
            log.write(pretty + "\n")

    request = Request(url=url, data=data, headers=headers, method=method)

    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else None
            return url, response.status, parsed
    except HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else raw
        except json.JSONDecodeError:
            parsed = raw
        return url, error.code, parsed
    except URLError as error:
        raise RuntimeError(f"Impossible d'appeler {url}: {error.reason}") from error


def get_value(data, dotted_path):
    current = data
    for part in dotted_path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as error:
                raise KeyError(f"Index introuvable dans la reponse: {dotted_path}") from error
            continue

        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Chemin introuvable dans la reponse: {dotted_path}")
        current = current[part]
    return current


def main():
    parser = argparse.ArgumentParser(description="Execute un scenario simple d'appels API.")
    parser.add_argument("scenario", nargs="?", default="scenario_tse1.json")
    args = parser.parse_args()

    scenario = load_json(args.scenario)
    base_url = scenario.get("base_url")
    if not base_url:
        print("Erreur: definir base_url dans le scenario.", file=sys.stderr)
        return 1

    variables = scenario.get("variables", {})

    with open("run.log", "w", encoding="utf-8") as log:
        log.write(f"Scenario: {args.scenario}\n")
        log.write(f"Base URL: {base_url}\n")

    for index, step in enumerate(scenario["steps"], start=1):
        name = step.get("name", f"step {index}")
        print(f"\n[{index}] {name}")

        url, status, response = call_api(base_url, step, variables)
        print(f"Status: {status}")
        print(json.dumps(response, indent=2, ensure_ascii=False))

        with open("run.log", "a", encoding="utf-8") as log:
            log.write(f"\n[{index}] {name}\n")
            log.write(f"{step.get('method', 'GET').upper()} {url}\n")
            log.write(f"Status: {status}\n")
            log.write(json.dumps(response, indent=2, ensure_ascii=False))
            log.write("\n")

        expected = step.get("expect_status")
        if expected is not None:
            # allow either a single expected status (int) or a list of acceptable statuses
            if isinstance(expected, list):
                ok = status in expected
            else:
                ok = status == expected

            if not ok:
                print(f"Erreur: status attendu {expected}, recu {status}", file=sys.stderr)
                with open("run.log", "a", encoding="utf-8") as log:
                    log.write(f"Erreur: status attendu {expected}, recu {status}\n")
                return 1

        for variable_name, response_path in step.get("save", {}).items():
            try:
                variables[variable_name] = get_value(response, response_path)
                saved_value = json.dumps(variables[variable_name], ensure_ascii=False)
                print(f"Variable sauvegardee: ${variable_name}={saved_value}")
                with open("run.log", "a", encoding="utf-8") as log:
                    log.write(f"Variable sauvegardee: ${variable_name}={saved_value}\n")
            except KeyError as e:
                print(f"Avertissement: impossible de sauvegarder ${variable_name} — chemin introuvable: {response_path}")
                print("Response complete:", json.dumps(response, indent=2, ensure_ascii=False))
                with open("run.log", "a", encoding="utf-8") as log:
                    log.write(f"Avertissement: impossible de sauvegarder ${variable_name} — chemin introuvable: {response_path}\n")
                    log.write("Response complete:\n")
                    log.write(json.dumps(response, indent=2, ensure_ascii=False) + "\n")

    print("\nScenario termine.")
    with open("run.log", "a", encoding="utf-8") as log:
        log.write("\nScenario termine.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
