# Sécurité de Noctis Auth

Noctis Auth manipule des secrets d’authentification à deux facteurs. La sécurité
du coffre et l’intégrité des mises à jour sont donc prioritaires.

## Signaler une vulnérabilité

N’ouvre **pas** d’issue publique contenant un secret, un coffre, un mot de passe,
une clé TOTP ou des données personnelles.

Utilise de préférence **GitHub → Security → Advisories → Report a vulnerability**
(Private vulnerability reporting) sur le dépôt. Indique :

- la version concernée ;
- les étapes de reproduction, sans secret réel ;
- l’impact estimé.

## Modèle de sécurité

- Coffre local : AES-256-GCM, nonce aléatoire de 12 octets par écriture.
- Dérivation : PBKDF2-HMAC-SHA256, sel aléatoire de 16 octets, 600 000 itérations.
- Le mot de passe principal n’est jamais stocké.
- Les secrets A2F ne sont jamais envoyés sur le réseau.
- Les écritures du coffre sont atomiques (`vault.tmp` puis remplacement).
- Aucune clé ni aucun code TOTP n’est généré ou simulé par l’application.

## Mises à jour

- Source unique : GitHub Releases du dépôt configuré dans `src/app_config.py`.
- Téléchargement HTTPS vers `%LOCALAPPDATA%\NoctisAuth\Updates`.
- Vérification **obligatoire** de l’empreinte SHA-256 publiée.
- Un fichier absent, incomplet ou dont l’empreinte diffère n’est jamais exécuté.
- L’installateur de mise à jour ne lit ni ne modifie `%APPDATA%\NoctisAuth`.

## Données et vie privée

- La vérification de mise à jour envoie uniquement une requête GET publique à
  `api.github.com`, avec un User-Agent générique `NoctisAuth/<version>`.
- Aucun identifiant de machine, aucune donnée du coffre, aucun code A2F.
- Les préférences locales (`settings.json`) ne contiennent qu’un booléen de
  vérification des mises à jour.
- Les journaux de compilation GitHub Actions ne contiennent aucune donnée locale.

## Dépôt

Ne jamais committer :

- `vault.json`, `settings.json` ou une sauvegarde de coffre ;
- des clés privées, certificats `.pfx`, mots de passe ou jetons ;
- des fichiers `.env` ;
- des captures contenant un code A2F ou un secret.

Le fichier `.gitignore` couvre ces cas. Vérifie toujours `git status` avant un tag.

## Désinstallation

Le désinstalleur supprime l’application et ses raccourcis. Le coffre
`%APPDATA%\NoctisAuth` est conservé, sauf si l’utilisateur coche explicitement
« Supprimer aussi mon coffre et mes comptes ».
