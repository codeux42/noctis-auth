# Noctis Auth

<p align="center">
  <img src="assets/noctis_logo.png" alt="Logo Noctis Auth" width="112">
</p>

<p align="center">
  <strong>Authentificateur TOTP (A2F) local, chiffré et sans compte en ligne.</strong><br>
  Windows 10 / 11 · interface liquid glass · 119 services · mises à jour vérifiées
</p>

<p align="center">
  <a href="https://github.com/codeux42/noctis-auth/releases/latest">
    <img alt="Dernière version" src="https://img.shields.io/github/v/release/codeux42/noctis-auth?style=flat-square&color=F4C542">
  </a>
  <a href="https://github.com/codeux42/noctis-auth/actions/workflows/build-release.yml">
    <img alt="Compilation" src="https://img.shields.io/github/actions/workflow/status/codeux42/noctis-auth/build-release.yml?style=flat-square">
  </a>
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=flat-square">
</p>

> Les liens ci-dessus utilisent le compte et le nom du dépôt GitHub. Après création
> du dépôt, lance `py scripts\configure_repo.py --owner TON_COMPTE --repo noctis-auth` :
> les badges, le lien de téléchargement et le système de mises à jour seront alignés.
> Le fichier `NoctisAuth_Setup.exe` est publié automatiquement dans **Releases**.

---

## Télécharger et installer

Un seul fichier suffit :

**[Télécharger NoctisAuth_Setup.exe](https://github.com/codeux42/noctis-auth/releases/latest/download/NoctisAuth_Setup.exe)**

1. Télécharge `NoctisAuth_Setup.exe` depuis la dernière Release.
2. Double-clique dessus. Aucun Python, aucune dépendance, aucun ZIP à extraire.
3. Choisis éventuellement un autre dossier, puis clique sur **Installer Noctis Auth**.
4. L’installation est effectuée pour l’utilisateur courant : **aucun droit administrateur**.
5. Un raccourci Bureau et une entrée dans le menu Démarrer sont créés.
6. Noctis Auth apparaît dans **Paramètres → Applications → Applications installées**.

### Vérifier l’intégrité du téléchargement

Chaque Release contient aussi `NoctisAuth_Setup.exe.sha256`. Dans PowerShell :

```powershell
Get-FileHash .\NoctisAuth_Setup.exe -Algorithm SHA256
Get-Content .\NoctisAuth_Setup.exe.sha256
```

Les deux empreintes doivent être identiques. L’application refuse également toute
mise à jour dont l’empreinte SHA-256 ne correspond pas.

### Avertissement SmartScreen

L’installateur n’est pas encore signé avec un certificat commercial. Windows peut
afficher « Windows a protégé votre ordinateur » : clique sur **Informations
complémentaires**, puis **Exécuter quand même**. Pour supprimer cet avertissement
en production, signe les deux exécutables avec un certificat Authenticode
(voir [Signature](#signature-des-exécutables)).

---

## Fonctionnalités

- **Coffre local chiffré AES-256-GCM**, clé dérivée par PBKDF2-SHA256 (600 000 itérations).
- **Aucun envoi de secret** : les clés A2F ne quittent jamais l’ordinateur.
- **119 services** avec recherche instantanée, catégories et alias.
- **Codes TOTP** calculés hors ligne, copie en un clic, anneau de compte à rebours.
- **Interface liquid glass** : boutons, champs et cartes rendus en images vectorielles.
- **Défilement natif corrigé** : la molette n’affecte que la liste survolée.
- **Ajout de compte** dans la page, avec vérification de la clé Base32.
- **Mises à jour GitHub** : détection, notes de version, téléchargement vérifié SHA-256.
- **Installateur graphique** avec pourcentage réel, raccourcis et désinstallation propre.
- **Données préservées** lors des mises à jour et des désinstallations (sauf demande explicite).

### Emplacements

| Élément | Chemin |
|---|---|
| Application | `%LOCALAPPDATA%\Programs\Noctis Auth\NoctisAuth.exe` |
| Désinstalleur | `%LOCALAPPDATA%\Programs\Noctis Auth\NoctisAuth_Setup.exe` |
| Coffre chiffré | `%APPDATA%\NoctisAuth\vault.json` |
| Préférences | `%APPDATA%\NoctisAuth\settings.json` |
| Cache de mise à jour | `%LOCALAPPDATA%\NoctisAuth\Updates` |

> **Ne supprime jamais `vault.json` sans sauvegarde.** Sans le mot de passe principal,
> le coffre ne peut pas être déchiffré. L’installateur et le désinstalleur ne le
> touchent pas, sauf si tu coches explicitement « Supprimer aussi mon coffre ».

---

## Structure du dépôt

```text
.
├── .github/workflows/build-release.yml   # CI : compilation + Release
├── assets/                               # logo, fond, ressources visuelles
├── docs/LISEZ-MOI.txt                    # notes utilisateur
├── packaging/
│   ├── NoctisAuth.spec                   # application onefile
│   └── NoctisAuth_Setup.spec             # installateur autonome
├── scripts/
│   ├── build.ps1                         # compilation complète
│   ├── build_gui.py                      # interface de compilation (BUILD.bat)
│   ├── bump_version.py                   # change la version partout
│   ├── check_version.py                  # contrôle tag / VERSION / code
│   ├── configure_repo.py                 # renseigne le dépôt de mises à jour
│   ├── make_checksum.py                  # empreintes SHA-256
│   ├── release.ps1                       # commit + tag + push
│   └── release_notes.py                  # notes extraites du CHANGELOG
├── src/
│   ├── app_config.py                     # version + dépôt GitHub (source unique)
│   ├── noctis_auth.py                    # application
│   ├── noctis_update.py                  # vérification des mises à jour
│   └── installer.py                      # installateur / désinstalleur
├── tests/
│   ├── test_update.py                    # versions, SHA-256, ressources
│   └── test_installer_flow.py            # installation silencieuse isolée
├── BUILD.bat                             # compilation en double-clic
├── VERSION
├── requirements.txt
├── requirements-build.txt
├── CHANGELOG.md
├── SECURITY.md
└── README.md
```

---

## Développement

Prérequis : **Python 3.11+** sur Windows et une connexion Internet pour les dépendances.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-build.txt
py src\noctis_auth.py
```

### Compiler

```powershell
.\scripts\build.ps1
```

ou double-clique sur `BUILD.bat` pour l’interface graphique de compilation.

Résultats :

- `dist/NoctisAuth.exe` — application portable ;
- `dist/NoctisAuth_Setup.exe` — installateur autonome à publier ;
- `dist/NoctisAuth_Setup.exe.sha256` — empreinte d’intégrité.

### Tests

```powershell
py -m unittest discover -s tests -v
```

---

## Créer le dépôt GitHub

```powershell
git init
git add .
git commit -m "Noctis Auth 2.9.0"
git branch -M main
```

Crée ensuite un dépôt **public** nommé `noctis-auth` (ou autre), puis :

```powershell
git remote add origin https://github.com/TON_COMPTE/noctis-auth.git
git push -u origin main
```

Renseigne le dépôt utilisé par le système de mises à jour :

```powershell
py scripts\configure_repo.py --owner TON_COMPTE --repo noctis-auth
git add src/app_config.py
git commit -m "Configure le dépôt de mises à jour"
git push
```

> Le workflow GitHub Actions réinjecte automatiquement le dépôt courant lors de
> chaque compilation (`configure_repo.py --from-environment`). La commande locale
> sert surtout aux compilations faites sur ta machine.

---

## Publier une nouvelle version

1. **Mets à jour le changelog** dans `CHANGELOG.md` :

   ```markdown
   ## [2.9.1] - 2026-12-01
   ### Corrigé
   - ...
   ```

2. **Change la version** (met à jour `VERSION`, `app_config.py` et les notes) :

   ```powershell
   py scripts\bump_version.py 2.9.1
   ```

3. **Commit, tag et push** :

   ```powershell
   git add -A
   git commit -m "Release v2.9.1"
   git tag v2.9.1
   git push origin main --tags
   ```

   Ou en une commande :

   ```powershell
   .\scripts\release.ps1 -Version 2.9.1
   ```

4. **GitHub Actions** compile automatiquement, vérifie la version, exécute les
   tests, construit `NoctisAuth_Setup.exe`, calcule son SHA-256 et crée la Release
   avec les fichiers :

   - `NoctisAuth_Setup.exe`
   - `NoctisAuth_Setup.exe.sha256`
   - `NoctisAuth.exe` (portable)
   - `NoctisAuth.exe.sha256`

5. Les utilisateurs reçoivent la mise à jour via **Paramètres → Vérifier les
   mises à jour** ou la pastille « Mise à jour disponible ».

Le tag, `VERSION` et `APP_VERSION` doivent être identiques, sinon la CI s’arrête
avant de publier.

---

## Système de mise à jour

- L’application interroge `https://api.github.com/repos/codeux42/noctis-auth/releases/latest`.
- La comparaison de versions est sémantique (`2.10.0` > `2.9.9`).
- Si aucune empreinte `.sha256` n’est publiée, la mise à jour est **refusée**.
- Le fichier est téléchargé dans `%LOCALAPPDATA%\NoctisAuth\Updates`, haché,
  comparé, puis seulement exécuté.
- L’installateur est lancé avec `/S /DIR=...` : mise à jour silencieuse, sans
  fenêtre de console, **sans toucher au coffre**.
- La vérification au démarrage est désactivable dans **Paramètres**.
- Aucun identifiant, aucune clé A2F et aucune donnée du coffre ne sont transmis.
  Seule une requête HTTPS publique vers GitHub est effectuée.

---

## Sécurité

Voir [SECURITY.md](SECURITY.md). En résumé :

- le coffre existant et son format AES-256-GCM sont conservés ;
- aucun secret, certificat ou mot de passe n’est présent dans le dépôt ;
- `vault.json`, `settings.json`, `.env` et les clés privées sont ignorés par Git ;
- les mises à jour sont vérifiées par SHA-256 avant exécution ;
- la désinstallation conserve les données sauf case cochée explicitement.

---

## Signature des exécutables

Pour supprimer l’avertissement SmartScreen, signe les exécutables avant publication
avec un certificat Authenticode (OV/EV) :

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /f certificat.pfx /p MOT_DE_PASSE dist\NoctisAuth.exe
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /f certificat.pfx /p MOT_DE_PASSE dist\NoctisAuth_Setup.exe
```

Ne commite jamais le certificat ni son mot de passe. Ajoute-les comme secrets
GitHub Actions et signe dans le workflow si nécessaire.

---

## Dépannage

| Problème | Solution |
|---|---|
| Windows bloque l’installateur | Informations complémentaires → Exécuter quand même, ou signer l’exe. |
| « Noctis Auth est encore ouvert » | Ferme l’application puis clique sur Réessayer. |
| La mise à jour n’est pas détectée | Vérifie le tag `vX.Y.Z` et la présence de `NoctisAuth_Setup.exe.sha256` dans la Release. |
| Le coffre ne s’ouvre plus | Le mot de passe principal est indispensable ; restaure une sauvegarde de `vault.json`. |
| La CI échoue sur la version | Aligne le tag, `VERSION` et `APP_VERSION` avec `scripts/bump_version.py`. |

---

## Licence

MIT — voir [LICENSE](LICENSE). Le logo et l’identité visuelle Noctis restent la
propriété de leur auteur.
