from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import tomllib

plt.rc('font', size=14)

CHEMIN_CONFIG = Path("config/resultat.toml")

def main():
    config = load_config()

    df = pd.read_csv(config["source"]["chemin"],
                     **config["source"]["read_csv_kwargs"])

    fig, ax = plt.subplots(**config["image"]["subplots_kwargs"])
    (df / 1000).T.plot.bar(ax=ax)
    ax.set_ylabel('k€')
    plt.xticks(rotation=90)
    ax.grid(True)
    fig.savefig(config["image"]["chemin_resultat"],
                **config["image"]["savefig_kwargs"])

    df_fin = pd.DataFrame(index=df.index, dtype=float)
    df_fin['Annuités'] = df['annuités']
    df_fin['Dotations aux amortissements'] = (
        df['dotations_amortissements_provisions'])
    df_fin['Besoin en financement'] = (
        config["destination"]["forfait_investissements"] *
        df['dotations_amortissements_provisions'] +
        df['annuités']
    )
    df_fin['Capacité économique'] = (
        (df['EBE_économique'] - df_fin['Besoin en financement']) /
        config["destination"]["etp_associe"]
    )

    fig, ax = plt.subplots(**config["image"]["subplots_kwargs"])
    (df_fin / 1000).T.plot.bar(ax=ax)
    ax.set_ylabel('k€')
    plt.xticks(rotation=90)
    ax.grid(True)
    fig.savefig(config["image"]["chemin_financement"],
                **config["image"]["savefig_kwargs"])

    df_ana = pd.DataFrame(index=df.index, dtype=float)
    df_ana['Efficience brute'] = df['valeur_ajoutée'] / df['production_nette']
    df_ana['EBE éco. / Prod. nette'] = (df['EBE_économique'] /
                                        df['production_nette'])
    df_ana['PP / EBE éco.'] = df['prélèvements_privés'] / df['EBE_économique']
    df_ana['Poids de la dette'] = df['annuités'] / df['EBE_économique']
    df_ana['RC éco. / Prod. nette'] = (df['résultat_courant_économique'] /
                                       df['production_nette'])
    df_ana['CO / Prod. nette'] = (df['charges_opérationnelles'] /
                                  df['production_nette'])
    co_sans_travail = (df['charges_opérationnelles'] -
                       df['travaux_délégués_opérationnels'])
    df_ana['CO s. W / Prod. nette'] = co_sans_travail / df['production_nette']
    df_ana['CS / Prod. nette'] = (df['charges_structure'] /
                                  df['production_nette'])
    df_ana['CP / Prod. nette'] = (df['charges_personnel'] /
                                  df['production_nette'])
    df_ana['CP a. op. / Prod. nette'] = (
        (df['charges_personnel'] + df['travaux_délégués_opérationnels']) /
        df['production_nette'])
    df_ana['AR / CA'] = (
        df['achats_de_marchandises_pour_revente'] *
        (1 + config["destination"]["marge_achat_revente"]) /
        df['chiffre_affaires']
    )
    df_ana['Sensibilité aux aides'] = (df['aides_structurelles'] /
                                       df['EBE_économique'])
    df_ana['CE / SMIC net'] = (df_fin['Capacité économique'] /
                               df['SMIC_annuel_net'])

    fig, ax = plt.subplots(**config["image"]["subplots_kwargs"])
    (df_ana * 100).T.plot.bar(ax=ax)
    ax.set_ylabel('%')
    plt.xticks(rotation=90)
    ax.set_ylim(0, 100)
    ax.grid(True)
    fig.savefig(config["image"]["chemin_analyse"],
                **config["image"]["savefig_kwargs"])

    etp = (df['salaires'] + df['cotisations_salariales'] +
           df['travaux_délégués_opérationnels']) / df['SMIC_annuel_brut']
    mb_sans_travail = df['production_nette'] - co_sans_travail
    total_heures = etp * config["destination"]["heures_par_an_salarie"]
    df_mb = pd.DataFrame(index=df.index, dtype=float)
    df_mb['MB globale / h'] =  mb_sans_travail/ total_heures
    df_mb['EBE éco. / h'] = df['EBE_économique'] / total_heures
    df_mb['EBE / h'] = df['EBE'] / total_heures
    df_mb["RE / h"] = df['résultat_exercice'] / total_heures

    fig, ax = plt.subplots(**config["image"]["subplots_kwargs"])
    df_mb.T.plot.bar(ax=ax)
    ax.set_ylabel('€ / h')
    plt.xticks(rotation=90)
    ax.grid(True)
    fig.savefig(config["image"]["chemin_mb"],
                **config["image"]["savefig_kwargs"])

    df_pm = pd.DataFrame(index=df.index, dtype=float)
    df_pm['Point mort'] = (
        df['charges_structure'] + df['travaux_délégués_opérationnels'] +
        df['dotations_amortissements_provisions']) / (
            df['production_nette'] -
            (df['charges_opérationnelles'] -
             df['travaux_délégués_opérationnels'])
        ) * 365

    df_pm['Point mort s. PP'] = (
        df['charges_structure'] + df['travaux_délégués_opérationnels'] +
        df['dotations_amortissements_provisions'] - 
        df['prélèvements_privés']) / (
            df['production_nette'] -
            (df['charges_opérationnelles'] -
             df['travaux_délégués_opérationnels'])
        ) * 365
    
    fig, ax = plt.subplots(**config["image"]["subplots_kwargs"])
    df_pm.T.plot.bar(ax=ax)
    ax.set_ylabel('jours')
    plt.xticks(rotation=90)
    ax.grid(True)
    fig.savefig(config["image"]["chemin_pm"],
                **config["image"]["savefig_kwargs"])

    plt.show(block=False)

def load_config():
    with open(CHEMIN_CONFIG, "rb") as f:
        config = tomllib.load(f)

    return config

if __name__ == "__main__":
    main()
