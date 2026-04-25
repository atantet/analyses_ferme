from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tomllib

pd.set_option('future.no_silent_downcasting', True)

CHEMIN_CONFIG = Path("config.toml")
COLONNES_PRODUITS = ["Produit", "Variante", "Pain produit"]

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

    # Lecture des prix des ingrédients
    s_prix_ingredients = pd.read_excel(
        config["prix_ingredients"]["chemin"],
        **config["prix_ingredients"]["read_excel_kwargs"])[
            config["prix_ingredients"]["colonne"]].sort_index().groupby(
                level=0).last()

    # Lecture des prix des produits
    s_prix_produits = pd.read_csv(
        config["prix_produits"]["chemin"],
        **config["prix_produits"]["read_csv_kwargs"])[
            config["prix_produits"]["colonne"]]
    
    # Préparation du tableau des quantités et des dépenses
    liste_ingredients = list(config["source"]["indices_ingredients"])
    df_quantite = pd.DataFrame(
        index=semaines[:-1], columns=liste_ingredients, dtype=float)
    df_quantite.index.name = "Semaine"
    df_depense = pd.DataFrame(
        index=semaines[:-1], columns=liste_ingredients, dtype=float)
    df_depense.index.name = "Semaine"

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
        for ingredient, indices_ingredients in config["source"][
                "indices_ingredients"].items():
            lignes, cols = zip(*indices_ingredients)
            df_quantite.loc[sem, ingredient] = (
                (df_ingredients_vendredi.to_numpy()[lignes, cols] +
                 df_ingredients_mardi.to_numpy()[lignes, cols])
            ).sum()

        # Produit
        df_produits_vendredi, df_poids_vendredi = (
            preparation_produits(df_vendredi, config))
        df_produits_mardi, df_poids_mardi = (
            preparation_produits(df_mardi, config))
        df_produits = df_produits_vendredi + df_produits_mardi
        df_poids = df_poids_vendredi + df_poids_mardi

        df_quantite.loc[sem, ["Pain produit", "Pain vendu"]] = (
            df_poids.sum("index"))
        df_quantite.loc[sem, ["CA théorique", "CA réalisé"]] = (
            df_produits.mul(s_prix_produits, axis="index").sum(
                "index").to_numpy())

    # Dépenses
    df_depense = df_quantite.mul(df_quantite.columns.to_series().map(
        s_prix_ingredients), axis="columns")[liste_ingredients]
    s_depense_totale = df_depense.sum("index")
    df_depense_totale = s_depense_totale.to_frame("Depense totale")

    # Sauvegarde des quantités
    # Pour ne pas traiter le sarrasin séparément, on le garde en farine
    quantite_farine_de_ble = (df_quantite["Farine T80"] +
                              df_quantite["Farine T65"] + 
                              df_quantite["Farine sarrasin"])
    df_quantite["Taux de perte de pain"] = (
        1 - df_quantite["Pain vendu"] / df_quantite["Pain produit"])
    df_quantite["Taux de perte de CA"] = (
        1 - df_quantite["CA réalisé"] / df_quantite["CA théorique"])
    df_quantite["Prix moyen"] = (df_quantite["CA réalisé"] /
                                 df_quantite["Pain vendu"])
    df_quantite["Besoin en blé"] = (
        quantite_farine_de_ble / 
        config["transformation"]["kg farine / kg blé"])
    df_quantite["kg pain / kg farine"] = (
        df_quantite["Pain produit"] / quantite_farine_de_ble)
    df_quantite["kg farine / kg blé"] = config["transformation"][
        "kg farine / kg blé"]
    df_quantite["kg blé / kg pain"] = 1 / (
        df_quantite["kg pain / kg farine"] * 
        df_quantite["kg farine / kg blé"])

    s_quantite_totale = df_quantite.sum("index")
    s_quantite_totale.loc[
        config["destination"]["quantites_moyennes"]] /= len(df_quantite)
    df_quantite_totale = s_quantite_totale.to_frame("Quantité totale")

    # Sauvegarde des quantités
    dossier = Path(config["destination"]["dossier"])
    chemin_quantite = dossier / Path(
        "quantite_" + config["source"]["année"] + ".csv")
    chemin_quantite.parent.mkdir(parents=True, exist_ok=True)
    df_quantite.to_csv(chemin_quantite)
    chemin_quantite_total = chemin_quantite.with_stem(
        chemin_quantite.stem + "_totale")
    df_quantite_totale.to_csv(chemin_quantite_total)

    dossier = Path(config["destination"]["dossier"])
    chemin_depense = dossier / Path(
        "depense_" + config["source"]["année"] + ".csv")
    chemin_depense.parent.mkdir(parents=True, exist_ok=True)
    df_depense.to_csv(chemin_depense)
    chemin_depense_total = chemin_depense.with_stem(
        chemin_depense.stem + "_totale")
    df_depense_totale.to_csv(chemin_depense_total)

    print("\n")
    print(df_quantite)
    print("\n")
    print(df_quantite_totale)
    print("\n")
    print(df_depense)
    print("\n")
    print(df_depense_totale)


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
            :, config["source"]["Colonnes produits"]].copy()
        df_produits.columns = COLONNES_PRODUITS

        # Suppression des pains gratuits
        cols_gratuit = [c for c in config["source"]["gratuit_pour"]
                        if c in df_produits_large.columns]
        df_selection = df_produits_large[cols_gratuit]
        df_produits.loc[:, "Pain vendu"] = (
            df_produits.loc[:, "Pain produit"] *
            (1 - config["destination"]["taux_de_perte"]) -
            df_selection.sum("columns")
        )

        # Remplissage des na
        df_produits.loc[:, "Variante"] = df_produits["Variante"].fillna(
            "Ordinaire")
        df_produits = df_produits.ffill(axis="index").set_index(
            ["Produit", "Variante"]).sort_index().groupby(
                level=[0, 1]).sum()

        # Lecture du tableau des correspondances des produits OTF
        df_corr = pd.read_csv(config["otf"]["chemin_correspondance"],
                              **config["otf"]["read_csv_kwargs"])

        # Faire correspondre l'indice avec OTF et calcul du poids
        index_otf = df_produits.index.map(df_corr["OTF"])
        df_produits_otf = df_produits.set_axis(index_otf)[
            index_otf.notna()]
        df_poids_kg_otf = df_produits.index.map(
            df_corr["Poids (kg)"]).to_series().set_axis(
                index_otf)[index_otf.notna()]
        df_poids_otf = df_produits_otf.mul(df_poids_kg_otf, axis="index")

        return df_produits_otf, df_poids_otf

if __name__ == "__main__":
    main()

