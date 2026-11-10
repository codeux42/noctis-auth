# Journal des versions

Toutes les versions publiées sont disponibles dans les
[Releases GitHub](https://github.com/codeux42/noctis-auth/releases).

## [2.9.1] - 2026-11-10

### Modifié

- Liste des services recentrée sur les services retenus pour l'ajout d'une clé TOTP/Base32.
- Logos de services affichés à partir de leurs favicons, avec cache local.
- Conservation du coffre chiffré et du calcul TOTP hors ligne.

## [2.9.0] - 2026-11-08

### Ajouté

- Installateur Windows autonome `NoctisAuth_Setup.exe`, sans Python ni console.
- Installation par utilisateur : aucun droit administrateur requis.
- Interface d’installation liquid glass avec logo, progression réelle et pourcentage.
- Raccourci Bureau optionnel, entrée dans le menu Démarrer et désinstalleur.
- Enregistrement dans **Applications installées** de Windows 10/11.
- Désinstallation propre avec conservation du coffre par défaut.
- Vérification des mises à jour via GitHub Releases, notes de version et téléchargement.
- Vérification obligatoire de l’empreinte SHA-256 de l’installateur.
- Mise à jour silencieuse (`/S`) qui conserve les comptes et le coffre.
- Workflow GitHub Actions de compilation et publication automatique.
- Scripts de version, de configuration du dépôt et de publication.

### Conservé

- Coffre AES-256-GCM, PBKDF2-SHA256 600 000 itérations et format `vault.json`.
- Interface liquid glass, 34 services compatibles TOTP, recherche instantanée et défilement corrigé.
- Calcul TOTP hors ligne, copie en un clic et modales personnalisées.

### Sécurité

- Aucun secret, certificat ou donnée utilisateur dans le dépôt.
- Les mises à jour sans empreinte SHA-256 sont refusées.
- Le coffre n’est jamais écrasé par une installation ou une mise à jour.

## [2.8.0] - 2026-11-08

### Ajouté

- Refonte « liquid glass » : boutons, champs et cartes rendus en images vectorielles.
- Icônes dessinées sur mesure et fenêtres modales en verre.
- 119 services avec recherche instantanée.
- Correction du défilement (molette routée vers la liste survolée).
- Animation de fond avec rubans lumineux et vignettage.

### Conservé

- Coffre local chiffré AES-256-GCM.
- Authentification TOTP hors ligne et vérification des clés Base32.
