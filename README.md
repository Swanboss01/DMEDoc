# DMEDoc (PREVIEW)

Outil de diagnostic **en lecture seule** pour calculateurs moteur BMW **MS42** (Siemens), pensé pour répondre à la question : *pourquoi ce calculateur ne fonctionne pas ?*

> ⚠️ **Version preview, jamais testée sur un vrai calculateur.** Les trames DS2 sont écrites d'après la documentation communautaire et les tests unitaires, pas validées sur matériel. Les retours de test sont les bienvenus (ouvrir une *issue* avec la sortie de `dmedoc check`).

## Ce que ça fait

| Commande | Rôle | Matériel |
|---|---|---|
| `dmedoc check --port COM3` | Interroge le calculateur en DS2 (identification + mémoire défauts) et explique les causes probables si pas de réponse | Câble K-line USB, calculateur alimenté |
| `dmedoc bin fichier.bin` | Analyse un dump : taille, zones effacées (0xFF), références, empreintes | Aucun |
| `dmedoc diff a.bin b.bin` | Compare deux dumps (ex. calculateur HS vs fichier sain) | Aucun |

## Ce que ça ne fait PAS

- Aucun flash, aucune écriture, aucun effacement. Pour lire/écrire le calculateur, utiliser **MS4x Flasher**.
- **Pas de vérification des checksums Siemens** (non implémentée) : `bin` détecte seulement les dumps manifestement incomplets.
- Le décodage des codes défaut n'est pas encore fait : les octets sont affichés bruts.

## Version Windows (.exe)

`DMEDoc.exe` (interface graphique, demande les droits administrateur) est joint à la *release* « preview ». Windows SmartScreen / Defender peut l'avertir car il n'est pas signé : c'est normal pour un exe PyInstaller non signé.

Pour le reconstruire : `pip install pyinstaller pyserial` puis
`pyinstaller --onefile --windowed --uac-admin --name DMEDoc run_gui.py`

Le mode graphique est aussi disponible avec `python -m dmedoc gui`.

## Installation (ligne de commande)

```
pip install pyserial
python -m dmedoc bin mon_dump.bin
python -m dmedoc check --port COM3
```

Câblage : K-line du calculateur ↔ interface compatible 12 V, DS2 à 9600 bauds 8E1, calculateur alimenté en 12 V avec contact (+15).

## Tests

```
python -m unittest discover tests
```

## Feuille de route

- Décodage des codes défaut et des valeurs en direct
- Vérification des checksums (après validation sur de vrais dumps)
- Banc de simulation voiture (vilebrequin 60-2, came, capteurs, EWS)

## Licence

MIT
