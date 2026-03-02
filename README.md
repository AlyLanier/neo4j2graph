# arcane2graph

## Executer arcane en sequentiel avec les options suivantes
```
-A,export_format=xml,export_output_directory=[path],export_only=true
```
!!! export_only sert à tuer le processus avant le lancement de la simultation en provoquant une erreur, l'erreur est donc normale.


## Convertir les configs .xml extraites via arcane en .json
```
python merge.py
```

**Note:** The `merge.py` script now handles both XML-to-JSON conversion and database import in a single command. The script automatically:
1. Converts XML files from `./xml` to JSON in `./arc_json`
2. Merges the JSON data into Neo4j
3. Imports AXL export files into Neo4j

## Installation & Setup with pip

### Quick Start (First Time Only)

1. **Create a local virtual environment:**
```bash
python3 -m venv .venv
```

2. **Activate it (Linux/Ubuntu Bash):**
```bash
source .venv/bin/activate
```

3. **Install the package:**
```bash
pip install -e .
```

### Running the Package

**After activation (recommended):**
```bash
source .venv/bin/activate
arcane2graph --help
arcane2graph --xml-path ./xml --json-path ./arc_json --neo4j-password password
```

**Without activation (one-off commands):**
```bash
./.venv/bin/arcane2graph --help
./.venv/bin/arcane2graph --xml-path ./xml
```

### What This Does
- Creates an isolated `.venv/` folder in your project
- Installs the package locally without affecting other projects
- Makes the `arcane2graph` command available
- The `-e` flag installs in development mode (changes to code take effect immediately)

---

## convertir les .axl en .json via axlstar
```
axl2ccT4 -l json -o \[output_path\] \[path_to_axl\]/Mahyco.axl
```

## Déploiement docker
```
docker run \
    -d \
    -p 7474:7474 -p 7687:7687 \
    -v $PWD/data:/data -v $PWD/plugins:/plugins \
    --name neo4j-apoc \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    -e NEO4J_PLUGINS=\[\"apoc\",\"apoc-extended\"\] \
    -e NEO4J_AUTH=neo4j/password \
    neo4j:5.26
```

## Remplir la BDD

Lancer **`merge.py`** qui exécute maintenant les trois étapes :
1. Conversion des fichiers XML en JSON
2. Fusion des données JSON dans Neo4j
3. Import des fichiers AXL export dans Neo4j

Une seule exécution du script suffit.

### Arguments de merge.py
```
python merge.py [OPTIONS]

Options:
  --xml-path PATH               Path to XML input directory (default: ./xml)
  --json-path PATH              Path to JSON directory - output of conversion and input for merge (default: ./arc_json)
  --skip-convert                Skip XML to JSON conversion step (default: false)
  --neo4j-uri URI               Neo4j connection URI (default: bolt://localhost:7687)
  --neo4j-username USERNAME     Neo4j username (default: neo4j)
  --neo4j-password PASSWORD     Neo4j password (default: password)
```

### Exemples
```bash
python merge.py --xml-path ./config/xml --json-path ./config/json --neo4j-uri bolt://localhost:7687 --neo4j-username neo4j --neo4j-password password
```

## Interface web
```
http://localhost:7474/browser/
```

## couple specification instance pour l'option nommée ...
```
MATCH p=(o: Option {fullName: "Mahyco/boundary-condition"})-[r:SPECIFIES]->()
return p
```

## Couverture de toutes les options
```
MATCH (o)-[:SPECIFIES]->(n)
WITH apoc.map.clean(properties(n), ['uid'], []) AS props, coalesce(o.fullName, o.name) AS name
UNWIND keys(props) AS key
RETURN name, key, props[key] AS value, count(*) AS count
ORDER BY name, count DESC;
```
