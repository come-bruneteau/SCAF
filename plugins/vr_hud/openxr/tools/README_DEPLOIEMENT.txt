SCAF OpenXR — Windows x64 portable
=================================

A effectuer seulement si les API layers utilisateur sont autorisees sur ce PC.
La couche peut etre chargee par toute application OpenXR de l'utilisateur.
Fermer DCS avant installation/desinstallation.

1. Extraire l'archive dans un dossier permanent et accessible en ecriture.
2. Verifier que la DLL et openxr-api-layer.json sont cote a cote.
3. Executer Install-User.cmd (ou demander au service informatique).
4. Ouvrir DCS en VR, puis lancer SCAF Core et le bridge Live.
5. Avant de deplacer/supprimer le dossier, executer Uninstall-User.cmd.

Il n'est pas necessaire d'installer Visual Studio sur le poste cible.
Il faut disposer de Python et des dependances SCAF pour le pont Live.
Si le PC applique AppLocker/WDAC/SmartScreen, demander une autorisation IT.
Un fichier CMD n'annule pas les politiques de securite Windows.

Verifier les enregistrements OpenXR (attention aux couches systeme en double) :
reg query HKCU\Software\Khronos\OpenXR\1\ApiLayers\Implicit
reg query HKLM\Software\Khronos\OpenXR\1\ApiLayers\Implicit
