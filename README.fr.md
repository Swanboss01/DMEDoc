# DMEDoc (PREVIEW)

[English](README.md) | Français

Outil de diagnostic **en lecture seule** pour calculateurs moteur BMW **MS42** (Siemens), pensé pour répondre à la question : *pourquoi ce calculateur ne fonctionne pas ?*

> ⚠️ **Version preview, jamais testée sur un vrai calculateur.** Les trames DS2 sont écrites d'après la documentation communautaire et les tests unitaires, pas validées sur matériel. Les retours de test sont les bienvenus (ouvrir une *issue* avec la sortie de `check`).

## Ce que ça fait

| Fonction | Rôle | Matériel |
|---|---|---|
| **Diagnostiquer le calculateur** (`dmedoc check --port COM3`) | Interroge le calculateur en DS2 (identification + mémoire défauts) et explique les causes probables s'il ne répond pas | Câble K-line USB, calculateur alimenté |
| **Analyser un .bin** (`dmedoc bin fichier.bin`) | Analyse un dump : taille, zones effacées (0xFF), références possibles, empreintes | Aucun |
| **Comparer deux .bin** (`dmedoc diff a.bin b.bin`) | Compare deux dumps (ex. calculateur HS vs fichier sain) | Aucun |

## Ce que ça ne fait PAS

- Aucun flash, aucune écriture, aucun effacement. Pour lire/écrire le calculateur, utiliser **MS4x Flasher**.
- **Pas de vérification des checksums Siemens** (non implémentée) : `bin` détecte seulement les dumps manifestement incomplets.
- Les codes défaut ne sont pas encore décodés : les octets sont affichés bruts.

## Installation Windows

À télécharger sur la page **Releases** :

- `DMEDoc-Setup-0.2.0.exe` : installateur (NSIS), avec raccourcis menu Démarrer / bureau et désinstallateur. En anglais ou en français.
- `DMEDoc.exe` : version portable, sans installation.

Les deux ouvrent une interface graphique et demandent les droits administrateur. Au premier lancement, le programme demande la langue (anglais ou français) ; le bouton *Langue* permet de la changer ensuite. Windows SmartScreen / Defender peut avertir pour un exécutable non signé.

Câblage : K-line du calculateur ↔ interface compatible 12 V, DS2 à 9600 bauds 8E1, calculateur alimenté en 12 V avec contact (+15).

## Depuis les sources

```
pip install pyserial
python -m dmedoc gui
python -m dmedoc bin mon_dump.bin
python -m dmedoc --lang fr check --port COM3
```

Construire les exécutables :

```
pip install pyinstaller pyserial
pyinstaller --onefile --windowed --uac-admin --name DMEDoc run_gui.py
makensis installer.nsi
```

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
