from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tomllib


pd.set_option('future.no_silent_downcasting', True)


CHEMIN_CONFIG = Path("config.toml")
COLONNES_PRODUITS = ["Produit", "Variante", "Quantité"]

def main():
    config = load_config()

    annee = config["source"]["année"]
    semaines = np.arange(53) + 1
    format_semaine = "%G%V%u"
    dates_vendredi = pd.to_datetime(
        [f"{annee}{str(s).zfill(2)}5" for s in semaines[:-1]],
        format=format_semaine)
    dates_mardi = pd.to_datetime(
        [f"{annee}{str(s).zfill(2)}2" for s in semaines[1:]],
        format=format_semaine)

    # Lecture des prix des produits
    s_prix = pd.read_csv(
        config["prix"]["chemin"],
        **config["prix"]["read_csv_kwargs"])["price_private"]
    
    # Préparation du tableau des quantités
    df_quantite = pd.DataFrame(
        index=semaines[:-1], columns=config["destination"]["ingredients"],
        dtype=float)
    df_quantite.index.name = "Semaine"

    for sem in semaines[:-1]:
        # Identification du fichier à lire
        date_mardi_cible = dates_mardi[sem - 1]
        f_src = list(Path(config["source"]["dossier"]).glob(
            f"S{sem:02d}S{(sem + 1 if sem < 52 else 1):02d}*.ods"))[0]
        print(f"\nLecture : {f_src.name}")

        # Sélection de la feuille du vendredi
        date_vendredi, feuille_vendredi, df_vendredi = (
            sel_feuille_vendredi(f_src, config))

        # Sélection de la bonne feuille pour le mardi
        date_mardi, feuille_mardi, df_mardi = sel_feuille_mardi(
            f_src, config, date_mardi_cible)

        print(f"Date vendredi : {date_vendredi} ({feuille_vendredi})")
        print(f"Date mardi : {date_mardi} ({feuille_mardi})")

        # Sélection des tableaux des ingrédients
        df_ingredients_vendredi = preparation_ingredients(
            df_vendredi, config)
        df_ingredients_mardi = preparation_ingredients(
            df_mardi, config)

        # Aggrégation des quantités d'ingrédients prévues
        for ingredient in config["destination"]["ingredients"]:
            lignes, cols = zip(*config["source"][ingredient])
            df_quantite.loc[sem, ingredient] = (
                df_ingredients_vendredi.to_numpy()[lignes, cols].sum() +
                df_ingredients_mardi.to_numpy()[lignes, cols].sum())

        # Produit
        s_produits_vendredi, s_poids_vendredi = (
            preparation_produits(df_vendredi, config))
        s_produits_mardi, s_poids_mardi = (
            preparation_produits(df_mardi, config))

        df_quantite.loc[sem, "CA"] = (
            (s_produits_mardi * s_prix).sum() + 
            (s_produits_vendredi * s_prix).sum())
        df_quantite.loc[sem, "Poids"] = (
            s_poids_mardi.sum() +  s_poids_vendredi.sum())

    df_quantite["Prix moyen"] = df_quantite["CA"] / df_quantite["Poids"]
    df_quantite["Besoin en blé"] = (
        (df_quantite["Farine T80"] + df_quantite["Farine T65"]) /
        config["transformation"]["kg farine / kg blé"])

    chem_rac = Path(config["destination"]["chemin"])
    chemin = chem_rac.with_stem(
        chem_rac.stem + "_" + config["source"]["année"])
    chemin.parent.mkdir(parents=True, exist_ok=True)
    df_quantite.to_csv(chemin)

    s_quantite_totale = df_quantite.sum("index")
    s_quantite_totale.loc["Prix moyen"] /= len(df_quantite)
    df_quantite_totale = s_quantite_totale.to_frame("Quantité totale")

    chemin_total = chemin.with_stem(chemin.stem + "_totale")
    df_quantite_totale.to_csv(chemin_total)

    print("\n")
    print(df_quantite)
    print("\n")
    print(df_quantite_totale)


def load_config():
    with open(CHEMIN_CONFIG, "rb") as f:
        config = tomllib.load(f)

    return config

def sel_feuille_vendredi(f, config):
    df = pd.read_excel(
        f, sheet_name=config["source"]["feuille_vendredi"],
        **config["source"]["read_excel_kwargs"])
    date = pd.to_datetime(df.iloc[*config["source"]["idx_date"]])
    feuille = config["source"]["feuille_vendredi"]

    return date, feuille, df

def sel_feuille_mardi(f, config, date_cible):
    df_paire = pd.read_excel(
        f, sheet_name=config["source"]["feuille_mardi_paire"],
        **config["source"]["read_excel_kwargs"])
    df_impaire = pd.read_excel(
        f, sheet_name=config["source"]["feuille_mardi_impaire"],
        **config["source"]["read_excel_kwargs"])

    date_paire = pd.to_datetime(
        df_paire.iloc[*config["source"]["idx_date"]])
    date_impaire = pd.to_datetime(df_impaire.iloc[
        *config["source"]["idx_date"]])
    if np.argmin([abs(date_paire - date_cible),
                  abs(date_impaire - date_cible)]) == 0:
        df = df_paire
        date = date_paire
        feuille = config["source"]["feuille_mardi_paire"]
    else:
        df = df_impaire
        date = date_impaire
        feuille = config["source"]["feuille_mardi_impaire"]

    return date, feuille, df


def preparation_ingredients(df, config):
    return df.iloc[
        config["source"]["Indices ingredients début"][0]:
        config["source"]["Indices ingredients fin"][0],
        config["source"]["Indices ingredients début"][1]:
        config["source"]["Indices ingredients fin"][1]
    ].fillna(config["source"]["valeur_de_remplissage"])

def preparation_produits(df, config):
        # Quantités de produits prévues
        df_produits_large = df.iloc[
            config["source"]["Indices produits début"][0]:
            config["source"]["Indices produits fin"][0],
            config["source"]["Indices produits début"][1]:
            config["source"]["Indices produits fin"][1]
        ].dropna(axis="index", how="all")
        df_produits = df_produits_large.iloc[
            :, config["source"]["Colonnes produits"]]
        df_produits.columns = COLONNES_PRODUITS

        # Suppression des pains gratuits
        cols_gratuit = [c for c in config["source"]["gratuit_pour"]
                        if c in df_produits_large.columns]
        df_selection = df_produits_large[cols_gratuit]
        df_produits.loc[:, "Quantité"] -= df_selection.sum("columns")
        
        df_produits.loc[:, "Variante"] = df_produits["Variante"].fillna(
            "Ordinaire")
        s_produits = df_produits.ffill(axis="index").set_index(
            ["Produit", "Variante"]).squeeze()
        s_produits = s_produits.sort_index().drop(
            ["Galettes amap", "Galettes plus"])

        # Lecture du tableau des correspondances des produits OTF
        df_corr = pd.read_csv(config["otf"]["chemin_correspondance"],
                              **config["otf"]["read_csv_kwargs"])

        # Faire correspondre l'indice avec OTF et calcul du poids
        index_otf = s_produits.index.map(df_corr["OTF"])
        s_poids_kg = s_produits.index.map(df_corr["Poids (kg)"])
        s_poids = s_produits * s_poids_kg
        s_produits = s_produits.set_axis(index_otf)
        s_poids = s_poids.set_axis(index_otf)

        return s_produits, s_poids

if __name__ == "__main__":
    main()

