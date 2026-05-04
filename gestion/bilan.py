from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import tomllib

plt.rc('font', size=14)

CHEMIN_CONFIG = Path("config/bilan.toml")

def main():
    config = load_config()

    df = pd.read_csv(config["source"]["chemin"],
                     **config["source"]["read_csv_kwargs"])

    fig, ax = plt.subplots(figsize=config["image"]["figsize_large"])
    (df / 1000).T.plot.bar(ax=ax)
    ax.set_ylabel('k€')
    plt.xticks(rotation=90)
    ax.grid(True)
    fig.savefig(config["image"]["chemin"], **config["image"]["kwargs"])

    df_ana = pd.DataFrame(index=df.index, dtype=float)

    df_ana["Capital d'exploitation"] = (
        df['total_actif'] - df['créances_associés'] -
        df['terrains_et_amenagement'])
    df_ana['Capitaux permanents'] = (
        df['total_capitaux_propres'] + df['dettes_associés'] +
        df['dettes_MLT'])

    fig, ax = plt.subplots()
    grandeurs = ["Capital d'exploitation", 'Capitaux permanents']
    (df_ana[grandeurs]  / 1000).T.plot.bar(ax=ax)
    ax.set_ylabel('k€')
    plt.xticks(rotation=90)
    ax.grid(True)
    fig.savefig(config["image"]["chemin_capital"],
                **config["image"]["kwargs"])

    df_ana['Fond de roulement net'] = (
        df_ana['Capitaux permanents'] - (
            df['total_actif_immobilisé'] + df['créances_associés']))
    df_ana['Fond de roulement net sur stock'] = (
        df_ana['Fond de roulement net'] / df['stocks_et_encours'])
    df_ana['Besoin en fond de roulement'] = (
        df['stocks_et_encours'] + df['avances_acomptes_fournisseurs'] +
        df['créances_exploitation'] +
        df['créances_hors_exploitation_autres']
        - df['avances_acomptes_clients'] - df['dettes_exploitation']
        - df['dettes_hors_exploitation_autres'])
    df_ana['Trésorerie nette'] = (
        df_ana['Fond de roulement net'] -
        df_ana['Besoin en fond de roulement'])
    df_ana['Trésorerie nette globale'] = (
        df['disponibilités'] + df['avances_acomptes_fournisseurs'] +
        df['créances_exploitation'] +
        df['créances_hors_exploitation_autres'] - (
            df['dettes_CT'] + df['avances_acomptes_clients'] +
            df['dettes_exploitation']))

    fig, ax = plt.subplots()
    grandeurs = ['Fond de roulement net', 'Besoin en fond de roulement',
                 'Trésorerie nette', 'Trésorerie nette globale']
    (df_ana[grandeurs]  / 1000).T.plot.bar(ax=ax)
    ax.set_ylabel('k€')
    plt.xticks(rotation=90)
    ax.grid(True)
    plt.legend(loc=(1.04, 0))
    fig.savefig(config["image"]["chemin_tn"], **config["image"]["kwargs"])


    df_ana["Taux d'endettement global"] = (
        (df['total_dettes'] - df['dettes_associés'] +
         df['créances_associés']) / df['total_passif'])
    df_ana["Taux d'endettement structurel"] = (
        df['dettes_MLT'] / df_ana['Capitaux permanents'])

    fig, ax = plt.subplots()
    grandeurs = ["Taux d'endettement global",
                 "Taux d'endettement structurel"]
    (df_ana[grandeurs]  * 100).T.plot.bar(ax=ax)
    ax.set_ylabel('%')
    plt.xticks(rotation=90)
    ax.grid(True)
    fig.savefig(config["image"]["chemin_taux"], **config["image"]["kwargs"])

    index = ['Court terme', 'Avances/acomptes', 'Exploitation',
             'Hors exploitation (non-associé)']
    for annee in df_ana.index:
        df_annee = df.loc[annee]
        df_stacked = pd.DataFrame(index=index, dtype=float)
        df_stacked['actif'] = df_annee[[
            'disponibilités',
            'avances_acomptes_fournisseurs',
            'créances_exploitation',
            'créances_hors_exploitation_autres'
            ]].values
        df_stacked['passif'] = df_annee[[
            'dettes_CT',
            'avances_acomptes_clients',
            'dettes_exploitation',
            'dettes_hors_exploitation_autres'
        ]].values

        fig, ax = plt.subplots()
        df_stacked.T.plot.bar(ax=ax, stacked=True)
        ax.set_ylabel(f'Montants pour {annee} (€)')
        ax.grid(True)
        fig.savefig(config["image"]["chemin_tng"],
                    **config["image"]["kwargs"])

    plt.show(block=False)

    chemin = Path(config["destination"]["chemin"])
    chemin.parent.mkdir(parents=True, exist_ok=True)
    df_ana.to_csv(chemin)

    return

def load_config():
    with open(CHEMIN_CONFIG, "rb") as f:
        config = tomllib.load(f)

    return config

if __name__ == "__main__":
    main()

