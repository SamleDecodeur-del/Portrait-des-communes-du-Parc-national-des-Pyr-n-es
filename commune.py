# communes.py
# =====================================================================================
# Préparation des données du « Portrait des communes du Parc national des Pyrénées ».
#
# Entrées  : donnees/communes_64_65.gpkg (IGN, ADMIN EXPRESS ; INSEE, population municipale),
#            donnees/pnp_coeur.geojson et donnees/pnp_aire_adhesion.geojson (DREAL Nouvelle-Aquitaine).
# Sorties  : donnees/communes_parc.pmtiles   (couches « communes » et « centres », lues par index.html)
#            donnees/parametres.json         (effectif maximal, année de population, emprise)
#            donnees/controle_*.csv          (pièces de contrôle de la sélection)
#
# Principe : pour chaque commune qui touche le Parc, on va mesure la part de son territoire en
# cœur, en aire d'adhésion et dans le Parc, puis on retient les communes selon deux seuils.
#
# =====================================================================================

import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

# ------------------------------------------------------------------------------------
# Paramètres
# ------------------------------------------------------------------------------------
GPKG_ENTREE = "donnees/communes_64_65.gpkg"
COEUR = "donnees/pnp_coeur.geojson"
AIRE = "donnees/pnp_aire_adhesion.geojson"

GPKG_SORTIE = "donnees/communes_parc.gpkg"        
PMTILES_SORTIE = "donnees/communes_parc.pmtiles"
PARAMETRES = "donnees/parametres.json"
CSV_COMMUNES = "donnees/controle_communes_retenues.csv"
CSV_COMPARAISON = "donnees/controle_precis_vs_generalise.csv"

# Seuils de sélection, exprimés en part de la surface communale (0.005 = 0,5 %).
# Les limites de l'IGN (communes) et de la DREAL (Parc) ne coïncident pas exactement : une
# commune voisine peut avoir un éclat infime dans le Parc. Les seuils sont placés dans le
# décrochage observé entre ces éclats et les communes réellement concernées.
SEUIL_PARC = 0.005    # part minimale dans le Parc (cœur + aire) pour retenir la commune
SEUIL_COEUR = 0.001   # part minimale en cœur pour classer la commune « cœur de parc »

# Bornes des classes de part de cœur (en %), utilisées pour imprimer la répartition.
BORNES_CLASSES = [0, 15, 30, 45, 100.01]

if not Path(GPKG_ENTREE).exists():
    sys.exit("Fichier introuvable : " + GPKG_ENTREE + "\n"
             "Lancer le script depuis le dossier qui contient « donnees ».")

for sortie in (GPKG_SORTIE, PMTILES_SORTIE, PARAMETRES, CSV_COMMUNES, CSV_COMPARAISON):
    Path(sortie).unlink(missing_ok=True)


def reunir(couche):
    """Fusionne une couche en une seule géométrie, après réparation des géométries invalides."""
    geoms = couche.geometry.make_valid()
    return geoms.union_all() if hasattr(geoms, "union_all") else geoms.unary_union


# ------------------------------------------------------------------------------------
# 1. Lecture et contrôle des systèmes de coordonnées
# ------------------------------------------------------------------------------------
communes = gpd.read_file(GPKG_ENTREE, layer="communes")        # tracé généralisé : affichage
precis = gpd.read_file(GPKG_ENTREE, layer="communes_precis")   # tracé précis : calcul des parts
coeur = gpd.read_file(COEUR)
aire = gpd.read_file(AIRE)

print("=== 1. Lecture ===")
print("EPSG  communes:", communes.crs.to_epsg(), "| précis:", precis.crs.to_epsg(),
      "| cœur:", coeur.crs.to_epsg(), "| aire:", aire.crs.to_epsg())
print("Communes :", len(communes), "| précises :", len(precis),
      "| code_insee uniques :", bool(communes["code_insee"].is_unique and precis["code_insee"].is_unique))

# Les surfaces se calculent dans un système en mètres : le cœur et l'aire
# sont reprojetés en Lambert-93 (EPSG:2154), le système des communes.
coeur = coeur.to_crs(2154)
aire = aire.to_crs(2154)
communes["geometry"] = communes.geometry.make_valid()
precis["geometry"] = precis.geometry.make_valid()

coeur_geom = reunir(coeur)
aire_geom = reunir(aire)
parc_geom = coeur_geom.union(aire_geom)   # le Parc : cœur + aire, sans double compte d'un éventuel recouvrement
print(f"Cœur : {coeur_geom.area / 1e6:.1f} km² | aire : {aire_geom.area / 1e6:.1f} km² | "
      f"recouvrement aire ∩ cœur : {aire_geom.intersection(coeur_geom).area / 1e6:.2f} km²")

# Contrôle de cohérence : surface_km2 (tracé généralisé) a été calculée sur le tracé précis
chk = precis[["code_insee"]].assign(surf_precise_km2=precis.geometry.area / 1e6)
chk = chk.merge(communes[["code_insee", "surface_km2"]], on="code_insee")
print(f"Écart maximal entre surface précise et surface_km2 : "
      f"{(chk['surf_precise_km2'] - chk['surface_km2']).abs().max():.4f} km²")


# ------------------------------------------------------------------------------------
# 2. Parts de cœur, d'aire et de Parc, sur chacun des deux tracés
# ------------------------------------------------------------------------------------
def mesurer(couche):
    """Surfaces en cœur, en aire et dans le Parc, et parts correspondantes (entre 0 et 1),
    pour les communes qui touchent le Parc."""
    candidates = couche[couche.intersects(parc_geom)]
    g = candidates.geometry
    res = pd.DataFrame({
        "code_insee": candidates["code_insee"].values,
        "surf_m2": g.area.values,
        "coeur_m2": g.intersection(coeur_geom).area.values,
        "aire_m2": g.intersection(aire_geom).area.values,
        "parc_m2": g.intersection(parc_geom).area.values,
    })
    for nom in ("coeur", "aire", "parc"):
        res["part_" + nom] = res[nom + "_m2"] / res["surf_m2"]
    return res


mes_gen = mesurer(communes)
mes_pre = mesurer(precis)   # référence pour les chiffres publiés

# ------------------------------------------------------------------------------------
# 3. Comparaison des deux tracés et classement des plus petites parts
# ------------------------------------------------------------------------------------
comp = mes_pre.merge(mes_gen, on="code_insee", how="outer", suffixes=("_pre", "_gen"))
comp = comp.merge(communes[["code_insee", "nom", "population"]], on="code_insee", how="left")
comp["parc_km2_pre"] = comp["parc_m2_pre"] / 1e6
comp.to_csv(CSV_COMPARAISON, index=False)

print("\n=== 3. Communes qui touchent le Parc ===")
print("Tracé précis :", len(mes_pre), "| tracé généralisé :", len(mes_gen))
sel_pre = set(mes_pre.loc[mes_pre["part_parc"] >= SEUIL_PARC, "code_insee"])
sel_gen = set(mes_gen.loc[mes_gen["part_parc"] >= SEUIL_PARC, "code_insee"])
print(f"Avec SEUIL_PARC = {SEUIL_PARC:.3%} : précis {len(sel_pre)} | généralisé {len(sel_gen)}")
print("Seulement dans le précis :", sorted(sel_pre - sel_gen))
print("Seulement dans le généralisé :", sorted(sel_gen - sel_pre))

print("\nLes 25 plus petites parts de Parc (tracé précis) :")
petits = (comp[comp["part_parc_pre"] > 0]
          .sort_values("part_parc_pre")
          .head(25)[["code_insee", "nom", "parc_km2_pre", "part_parc_pre", "part_parc_gen"]])
print(petits.to_string(index=False, float_format=lambda x: f"{x:.6f}"))

# ------------------------------------------------------------------------------------
# 4. Sélection et attributs
#    Les parts viennent du tracé précis ; la géométrie affichée est le tracé généralisé,
#    plus léger.
# ------------------------------------------------------------------------------------
retenues = mes_pre[mes_pre["part_parc"] >= SEUIL_PARC].copy()
retenues["coeur_km2"] = (retenues["coeur_m2"] / 1e6).round(2)
retenues["aire_km2"] = (retenues["aire_m2"] / 1e6).round(2)
retenues["part_coeur_pct"] = (retenues["part_coeur"] * 100).round(1)
retenues["part_aire_pct"] = (retenues["part_aire"] * 100).round(1)
retenues["part_parc_pct"] = (retenues["part_parc"] * 100).round(1)
retenues["en_coeur"] = (retenues["part_coeur"] >= SEUIL_COEUR).astype(int)   
retenues["statut"] = np.where(retenues["en_coeur"] == 1, "cœur de parc", "aire d'adhésion seule")

champs = ["code_insee", "nom", "departement", "population", "date_population", "surface_km2", "geometry"]
garder = ["code_insee", "coeur_km2", "aire_km2", "part_coeur_pct", "part_aire_pct",
          "part_parc_pct", "en_coeur", "statut"]
couche_communes = (communes[champs]
                   .merge(retenues[garder], on="code_insee", how="inner")
                   .sort_values("population", ascending=False)
                   .reset_index(drop=True))

# Un point par commune pour les cercles proportionnels. representative_point() garantit un
# point à l'intérieur de la commune, ce que le centroïde ne fait pas pour une commune concave.
centres = couche_communes.copy()
centres["geometry"] = couche_communes.geometry.representative_point()
assert centres.geometry.within(couche_communes.geometry).all(), "un point sort de sa commune"

# ------------------------------------------------------------------------------------
# 5. Export : GeoPackage à deux couches (EPSG:4326) puis PMTiles
# ------------------------------------------------------------------------------------
couche_communes.to_crs(4326).to_file(GPKG_SORTIE, layer="communes")   # polygones
centres.to_crs(4326).to_file(GPKG_SORTIE, layer="centres")            # points
subprocess.run([
    "ogr2ogr", "-f", "PMTiles", PMTILES_SORTIE, GPKG_SORTIE,
    "-dsco", "MINZOOM=6", "-dsco", "MAXZOOM=12",   # tracé généralisé : pas de zoom utile au-delà
    "-preserve_fid",                               # un identifiant par entité
], check=True)

# Valeurs dont la page a besoin et qu'elle ne peut pas déduire des tuiles :
# effectif maximal (échelle des cercles), année de la population (légende), emprise (cadrage).
parametres = {
    "n_communes": int(len(couche_communes)),
    "pop_max": int(couche_communes["population"].max()),
    "annee_population": sorted({str(d)[:4] for d in couche_communes["date_population"]}),
    "emprise": [float(x) for x in couche_communes.to_crs(4326).total_bounds],   # ouest, sud, est, nord
    "seuil_parc": SEUIL_PARC,
    "seuil_coeur": SEUIL_COEUR,
}
with open(PARAMETRES, "w", encoding="utf-8") as f:
    json.dump(parametres, f, ensure_ascii=False, indent=2)

couche_communes.drop(columns="geometry").to_csv(CSV_COMMUNES, index=False)

# ------------------------------------------------------------------------------------
# Contrôles (détails dans le readme)
# ------------------------------------------------------------------------------------
print("\n=== Contrôles ===")
n_coeur = int(couche_communes["en_coeur"].sum())
print("Communes retenues :", len(couche_communes),
      "| avec du cœur :", n_coeur, "| aire d'adhésion seule :", len(couche_communes) - n_coeur)
print("Population cumulée des communes retenues (communes entières) :",
      int(couche_communes["population"].sum()))
print("Année(s) de la population :", parametres["annee_population"])
print("Plus grand effectif :", parametres["pop_max"],
      "->", couche_communes.loc[couche_communes["population"].idxmax(), "nom"])
print("Poids du PMTiles :", round(Path(PMTILES_SORTIE).stat().st_size / 1024), "Ko")

print("\nPart de cœur des communes qui ont du cœur (en %) :")
parts_coeur = couche_communes.loc[couche_communes["en_coeur"] == 1, "part_coeur_pct"]
print(parts_coeur.describe().round(1).to_string())
repartition = pd.cut(parts_coeur, bins=BORNES_CLASSES, right=False).value_counts().sort_index()
print("Répartition dans les classes de la carte :")
print(repartition.to_string())

print("\nTerminé :", PMTILES_SORTIE, "et", PARAMETRES)
