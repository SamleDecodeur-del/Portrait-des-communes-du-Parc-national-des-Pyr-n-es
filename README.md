# Portrait des communes du Parc national des Pyrénées

## Choix

- **Sélection des communes (`SEUIL_PARC`) :** une commune est retenue si au moins **0,5 %** (`0.005`) de sa surface est dans le Parc (cœur + aire d'adhésion) sur le tracé précis. Sur les 107 communes ayant une intersection non nulle avec le Parc sur ce tracé, les 38 premières ont des parts minuscules (à partir d'environ `0,000000008 %` et moins de `0,001 km²` intersectés), correspondant à des éclats liés au décalage entre limites IGN et DREAL. Classées par part dans le Parc croissante, les valeurs bondissent nettement à la 39ᵉ ligne avec **Lescun** (environ `11,81 %`, soit `7,29 km²`). On retient ainsi **69 communes** (contrôle réalisé à partir du CSV généré et inspecté dans VS Code).
- **Seuil pour le statut cœur (`SEUIL_COEUR`) :** fixé à **0,1 %** (`0.001`) de la surface communale en cœur de parc, afin d'écarter le micro-recouvrement de **Saint-Lary-Soulan** (`~6 m²`, soit environ `0,000007 %`) tout en conservant les **14 communes** ayant un véritable territoire en cœur de parc (à partir de **Betpouey** à `2,36 %`).
- **Part du territoire en cœur (taux) :** représentée en aplat par classes avec une palette monochrome du clair au foncé (bornes dans `index.html` : `0`, `10`, `30`, `60`). Les communes en aire d'adhésion seule sont distinguées par une couleur grise neutre.
- **Population (effectif) :** représentée par des cercles proportionnels à la population (rayon proportionnel à la racine carrée de la population), triés afin que les plus petits cercles restent visibles au-dessus des plus grands.

## Contrôles

- **Systèmes de coordonnées :** vérifiés avant croisement : communes en `EPSG:2154`, cœur et aire d'adhésion reprojetés de `EPSG:4326` vers `EPSG:2154`.
- **Écart entre `surface_km2` et la surface recalculée sur le tracé précis :** `0,0050 km²` (écart maximal constaté).
- **Communes touchant le Parc :** `107` (précis), `112` (généralisé) ; retenues avec le seuil de `0,5 %` : `69` (précis), `100` (généralisé) ; différences : `0` uniquement dans le précis, `31` uniquement dans le généralisé à ce seuil.
- **Population cumulée des communes retenues (communes entières) :** `31 164` habitants (millésime INSEE `2022`, maximum `7 060` à Bagnères-de-Bigorre)[cite: 2].
- **Position des points de cercles :** chaque point est dans sa commune (`representative_point()`, vérifié par assertion du script)[cite: 2].
- **Poids de `donnees/communes_parc.pmtiles` :** `138 Ko`.
- **Console du navigateur :** aucune erreur ni avertissement *(à compléter avec la date et l'environnement de test)*.
- **Affichage mobile / vue adaptative :** *(à compléter après test sur téléphone ou en vue adaptative Firefox)*.

## Limites

- **Population communale ≠ population dans le Parc :** la population affichée correspond à la commune entière ; la carte ne dit pas combien d'habitants résident effectivement dans le Parc.
- **Part de surface ≠ occupation du territoire :** une part élevée de territoire en cœur de parc ne reflète pas la répartition de l'habitat ni l'usage des sols (une commune peut avoir du cœur uniquement en haute montagne).
- **Millésime de la population (`date_population`) :** les données reflètent l'année `2022` ; malgré les modalités de recensement en France, cela reste une limite temporelle de la carte.
- **Lisibilité des petites populations :** avec une surface de cercle proportionnelle à l'effectif, les très petits cercles sont peu visibles à l'échelle d'ensemble.

## Journal de bord

- Mise en place : récupération des données du TP et lancement de serveur.py sur le port 5000 pour les tests d'affichage.
- Préparation et choix des seuils : exécution de communes.py, inspection de controle_precis_vs_generalise.csv pour repérer les éclats (dont Saint-Lary-Soulan sur le cœur) et le décrochage à partir de Lescun, puis réglage des seuils (SEUIL_PARC et SEUIL_COEUR) et relance pour générer communes_parc.pmtiles et parametres.json.   
- Carte et contrôles : vérification du rendu dans index.html (aplats de part de cœur, cercles proportionnels, fiche au clic, légende repliée sur petit écran, mentions de crédit) et contrôle de la console sans erreur ni avertissement.
- Publication : dépôt des fichiers utiles sur un dépôt GitHub public et activation de GitHub Pages (sans verser le GeoPackage d'entrée volumineux). 
