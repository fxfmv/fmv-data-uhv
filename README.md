# API workflow tester

Canevas minimal pour lancer un scenario d'appels API `GET`, `POST` et `DELETE`.

## Lancer

```powershell
python .\run_scenario.py .\scenario_tse1.json
```

## Modifier le scenario

Edite ton fichier de scenario, par exemple `scenario_tse1.json`.

- `base_url`: serveur cible
- `steps`: appels executes dans l'ordre
- `expect_status`: status HTTP attendu
- `save`: sauvegarde une valeur de la reponse pour la reutiliser plus tard

Exemple:

```json
"save": {
  "item_id": "id"
}
```

Ensuite tu peux reutiliser `$item_id` dans un `path`, un `header` ou un `body`.
