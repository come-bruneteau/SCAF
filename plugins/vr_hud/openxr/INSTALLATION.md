# SCAF OpenXR — Installation et déploiement

## État et périmètre

Ce module fournit un HUD expérimental **transparent et fixé à la tête** dans DCS World en VR, au moyen d'une couche d'API OpenXR. Les essais VR-004 (télémétrie Live) et VR-005.1 (affichage compact, indicateur de roulis lissé) ont été validés sur le poste de développement avec un Meta Quest 3. **La compilation depuis un clone neuf et le déploiement sur un poste ENSC administré restent à valider.**

Une couche implicite OpenXR peut être chargée par toutes les applications OpenXR du même utilisateur. Fermer DCS pour installer, désinstaller ou remplacer la DLL. Ne pas enregistrer simultanément plusieurs copies du même HUD.

## Dépendances

**Développement / compilation (Windows 10/11 x64) :**
- Git ; Python 3.10+ ; Visual Studio 2022, charge de travail « Développement Desktop en C++ » ; composants Windows SDK / NuGet nécessaires au template.
- DCS World en VR utilisant OpenXR, Quest Link ou runtime équivalent.

**PC cible sans Visual Studio :**
- DCS World + casque + runtime OpenXR déjà fonctionnels ; Python 3 et dépendances SCAF pour le pont Live.
- Autorisation d'utiliser une couche OpenXR par utilisateur et une DLL non signée, conformément aux règles informatiques locales.

## A. Préparer le build (sur le PC développeur)

Ouvrir PowerShell **à la racine de SCAF** :

```powershell
python plugins/vr_hud/openxr/tools/prepare_build.py
```

Le script récupère le template MIT `mbucchia/OpenXR-Layer-Template`, l'ancre sur le commit `2827205005310dfb799226f5d197afe253a5d4ab`, applique l'intégration SCAF à `layer.cpp`, puis copie le HUD actuel `src/scaf_hud.h`.

En cas d'ancien `vendor/` déjà modifié par nos anciens sprints : le script peut signaler un conflit. **Sauvegarder d'abord les modifications locales importantes.** Pour régénérer volontairement le template à partir de zéro :

```powershell
python plugins/vr_hud/openxr/tools/prepare_build.py --reset-vendor
```

> `--reset-vendor` supprime le checkout ignoré `vendor/OpenXR-Layer-Template`, **pas** les sources suivies dans SCAF. Le faire seulement après sauvegarde des changements locaux. Le script n'effectue aucune modification du registre.

Ouvrir ensuite :

```text
plugins/vr_hud/openxr/vendor/OpenXR-Layer-Template/XR_APILAYER_NOVENDOR_template.sln
```

Dans Visual Studio, choisir **Release | x64**, puis **Build → Rebuild Solution**. Ne pas tenter d'exécuter la DLL avec le débogueur comme une application autonome.

Le résultat attendu se trouve ici :

```text
plugins/vr_hud/openxr/vendor/OpenXR-Layer-Template/bin/x64/Release/
  openxr-api-layer.json
  XR_APILAYER_NOVENDOR_template.dll
```

Le nom exact de la DLL doit correspondre à `api_layer.library_path` dans le JSON.

## B. Tester le HUD sur le poste développeur

Installer d'abord les dépendances SCAF :

```powershell
.\install.bat
```

### Mode démonstration, sans DCS Core

Dans un terminal :

```powershell
.\.venv\Scripts\python.exe -m plugins.vr_hud.openxr.bridge --demo
```

Le pont envoie des valeurs simulées à `127.0.0.1:50502`. Le HUD injecté les affiche lorsque DCS tourne en VR.

### Mode réel

Dans deux terminaux différents :

```powershell
.\.venv\Scripts\python.exe -m core.networking.receiver
```

```powershell
.\.venv\Scripts\python.exe -m plugins.vr_hud.openxr.bridge
```

Installer `core/dcs/lua/Export.lua` dans `Saved Games/DCS/Scripts/Export.lua`, **sans écraser** une intégration `Export.lua` préexistante : fusionner les callbacks si nécessaire. Le flux suit UDP 50500 → WebSocket 50501 → UDP 50502 → couche OpenXR.

## C. Générer l'archive GitHub Release

**Après validation du build dans le casque**, depuis la racine :

```powershell
python plugins/vr_hud/openxr/tools/make_release.py
```

Le script existant produit :

```text
plugins/vr_hud/openxr/dist/releases/
  SCAF-OpenXR-Windows-x64.zip
  SCAF-OpenXR-Windows-x64.zip.sha256
```

L'archive contient la DLL, son manifeste et des scripts `.cmd` d'enregistrement/désenregistrement HKCU. `vendor/` et `dist/` restent exclus de Git ; on publie l'archive dans GitHub Releases, pas dans `main`.

Exemple avec GitHub CLI après push et validation :

```powershell
gh auth login
gh release create vr-0.5.1 `
  plugins/vr_hud/openxr/dist/releases/SCAF-OpenXR-Windows-x64.zip `
  plugins/vr_hud/openxr/dist/releases/SCAF-OpenXR-Windows-x64.zip.sha256 `
  --repo come-bruneteau/SCAF --target main `
  --title "SCAF OpenXR VR 0.5.1" --prerelease `
  --notes "Experimental transparent head-locked HUD and live telemetry."
```

## D. Installer sur le PC de l'ENSC (sans compilation)

1. Vérifier que l'ENSC **autorise** l'exécution de cette DLL et l'enregistrement de couches OpenXR utilisateur.
2. Télécharger la release, vérifier l'empreinte SHA256 avec `Get-FileHash`, puis décompresser dans un dossier **permanent** et accessible en lecture.
3. Fermer DCS et lancer `Install-User.cmd` depuis le dossier extrait. Ce script inscrit le manifeste dans `HKCU\Software\Khronos\OpenXR\1\ApiLayers\Implicit` sans demande d'élévation.
4. Reprendre le clone SCAF sur le PC, lancer `install.bat` puis les deux processus Python Core et bridge (voir B).
5. Relancer DCS en VR et valider télémétrie, transparence, assiette et fluidité.
6. Avant de déplacer/supprimer le dossier de release, exécuter `Uninstall-User.cmd`.

**Sécurité :** l'utilisation d'un `.cmd` évite la politique de signature PowerShell pour les `.ps1`, mais ne contourne pas AppLocker, WDAC ou les restrictions administratives de l'école. En cas de blocage, demander une autorisation au service informatique. Aucune modification HKLM n'est requise pour l'installation utilisateur.

## E. Dépannage

- **Ancien HUD statique ou double affichage :** vérifier l'enregistrement HKCU et d'éventuelles entrées HKLM héritées. Supprimer uniquement les enregistrements SCAF dont on connaît le manifeste ; ne pas toucher aux autres couches.
- **Le HUD s'affiche mais ne change pas :** vérifier le pont `bridge --demo`, le port UDP local 50502 et la DLL réellement chargée.
- **Tirets à la place des mesures :** s'assurer que SCAF Core et le pont Live sont démarrés et que DCS exporte des paquets.
- **Le test fonctionne sur un PC mais pas l'autre :** vérifier l'architecture x64, le runtime OpenXR et les politiques de sécurité. L'enregistrement HKCU seul ne garantit pas qu'une DLL non signée soit autorisée.
- **Fluidité de l'indicateur de roulis :** l'assiette reçue à ~5 Hz est l'actuel facteur limitant ; augmenter sa fréquence relève d'un prochain sprint indépendant.

## F. Tests et licence

Depuis la racine :

```powershell
python -m unittest discover -s plugins/vr_hud/openxr/tests -v
python -m unittest discover -s tests -v
```

Le code OpenXR utilise un template tiers sous licence MIT. Conserver les mentions de copyright et les licences d'origine des dépendances utilisées dans toute distribution appropriée.
