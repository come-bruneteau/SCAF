SCAF OpenXR - Windows x64
=========================

Installation portable du HUD VR SCAF
Version : VR-005.1 (experimental)

Ce package permet d'utiliser le HUD SCAF dans DCS World avec un casque VR compatible OpenXR, sans installer Visual Studio sur le PC cible.

Le HUD est transparent, fixe par rapport a la tete (head-locked) et affiche les donnees de vol en temps reel.

IMPORTANT
---------

- L'installation utilise le registre de l'utilisateur Windows (HKCU).
- Aucun droit administrateur n'est normalement necessaire.
- L'etablissement doit autoriser les extensions OpenXR tierces.
- Les politiques AppLocker, WDAC ou antivirus peuvent bloquer la DLL.
- Ne jamais deplacer le dossier apres l'installation sans desinstaller la couche.
- Fermer DCS avant toute installation ou desinstallation.

1. PREREQUIS
------------

- Windows 10 ou 11 x64
- DCS World fonctionnel en VR
- Runtime OpenXR compatible et operationnel
- Casque VR compatible (Meta Quest 3 teste)
- Python 3 avec les dependances SCAF
- Depot SCAF disponible pour le noyau et le pont Live

Visual Studio n'est PAS necessaire sur le PC cible.

2. CONTENU DU PACKAGE
---------------------

SCAF-OpenXR-Windows-x64/
    XR_APILAYER_NOVENDOR_template.dll
    openxr-api-layer.json
    Install-User.cmd
    Uninstall-User.cmd
    README_DEPLOIEMENT.txt

La DLL et son manifeste doivent rester dans le meme dossier.

3. INSTALLATION
---------------

1. Extraire l'archive ZIP dans un dossier permanent.
2. Verifier que la DLL et le manifeste sont presents.
3. Fermer DCS et les autres applications OpenXR.
4. Executer Install-User.cmd depuis le dossier extrait.
5. Verifier que l'enregistrement utilisateur a reussi.
6. Relancer DCS en VR.

Cette operation n'installe pas de logiciel systeme et n'exige normalement pas d'elevation administrateur.

4. DEMARRAGE DE SCAF
--------------------

Depuis la racine du depot SCAF, ouvrir deux terminaux.

Terminal 1 - Noyau SCAF :

    .\.venv\Scripts\python.exe -m core.networking.receiver

Terminal 2 - Pont OpenXR Live :

    .\.venv\Scripts\python.exe -m plugins.vr_hud.openxr.bridge

Ensuite, lancer DCS World en VR et demarrer une mission.

Flux de donnees :

    DCS World
       -> UDP 50500
    SCAF Core
       -> WebSocket 50501
    Pont Python
       -> UDP 50502
    HUD OpenXR
       -> Casque VR

Ne pas lancer plusieurs instances du recepteur ou du pont sur les memes ports.

5. TEST SANS TELEMETRIE DCS
---------------------------

Pour verifier uniquement l'affichage dynamique :

    .\.venv\Scripts\python.exe -m plugins.vr_hud.openxr.bridge --demo

Le HUD doit afficher des mesures simulees qui evoluent.

Ces mesures sont fictives et ne representent pas l'etat de l'avion.

Arreter ce mode avec Ctrl+C avant de passer au mode Live.

6. DEPANNAGE
------------

HUD absent :
- Verifier le runtime OpenXR actif.
- Verifier l'enregistrement de la couche.
- Verifier le chemin du manifeste et de la DLL.
- Redemarrer completement DCS.
- Verifier les restrictions informatiques du PC.

HUD visible mais sans valeurs :
- Verifier le demarrage de SCAF Core et du pont Python.
- Verifier les ports locaux 50500, 50501 et 50502.
- Verifier que DCS exporte bien sa telemetrie.
- Tester le pont avec --demo.

Ancien HUD ou affichage double :
- Verifier les anciennes installations de la couche.
- Eviter plusieurs enregistrements actifs de SCAF.
- Ne supprimer que les enregistrements dont l'origine est connue.

Commandes de diagnostic :

    reg query HKCU\Software\Khronos\OpenXR\1\ApiLayers\Implicit
    reg query HKLM\Software\Khronos\OpenXR\1\ApiLayers\Implicit

En cas de restrictions imposees par l'ENSC, contacter le service informatique. Ne pas contourner les politiques du poste.

7. DESINSTALLATION
------------------

1. Fermer DCS.
2. Executer Uninstall-User.cmd depuis le dossier installe.
3. Verifier que l'enregistrement a ete supprime.
4. Supprimer le dossier du package si necessaire.

Toujours desinstaller la couche AVANT de deplacer ou supprimer le dossier.

8. LIMITATIONS
--------------

- Version experimentale destinee a la simulation.
- Affichage head-locked ; marqueurs world-locked non disponibles.
- La fluidite de l'horizon depend de la frequence de telemetrie.
- Les performances peuvent varier selon le PC, DCS et le runtime OpenXR.
- Aucune utilisation pour le pilotage d'un aeronef reel.

Projet SCAF - ENSC / Bordeaux INP
Repository : https://github.com/come-bruneteau/SCAF