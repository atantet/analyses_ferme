from pathlib import Path

from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tomllib

CHEMIN_CONFIG = Path("config/ca.toml")

plt.rc('font', size=12)
COLORS = plt.rcParams['axes.prop_cycle'].by_key()['color']

def main():
    config = load_config()

    # Lecture des tableurs de recettes par année
    data = []
    for annee in config["source"]["annees"]:
        dossier = Path(config["source"]["racine"]) / Path(annee)
        fichier = Path(f"chiffre d'affaire {annee}.ods")
        df_annee = pd.read_excel(
            dossier / fichier,
            **config["source"]["read_excel_kwargs"]
        )
        df_annee = df_annee.loc[~df_annee['Année'].isnull()]
        date_dict = {
            'year': df_annee['Année'],
            'month': df_annee['Mois'],
            'day': df_annee['Jour']
        }
        index = pd.to_datetime(date_dict)
        df_annee = df_annee.set_index(index)
        df_annee['CA'] = df_annee[config["source"]["colonne_ca"]].sum(
            'columns')
        data.append(df_annee)
    df = pd.concat(data)
    # Conversion en HT en supposant à tort que tout est TTC
    df = df.apply(lambda col: col / (1 + config["debouche"]["TVA"])
                  if col.dtype == float else col)
    calendrier = df.index.isocalendar()

    # Ventilation par débouché
    df_debouches = pd.DataFrame(index=df.index, dtype=float)
    for debouche, jour in config["debouche"]["jour"].items():
        index_debouche = calendrier['day'] == jour
        if debouche == 'Marché bio de Dol':
            index_debouche &= ((calendrier['week'] % 2) ==
                               config["debouche"]["parite_marche_bio"])
        elif debouche == 'Pain au marché bio de Dol':
            index_debouche &= ((calendrier['week'] % 2) !=
                               config["debouche"]["parite_marche_bio"])
        df_debouches[debouche] = df['CA'].where(index_debouche)
    df_debouches_par_semaine = df_debouches.groupby(
        [calendrier['year'], calendrier['week']]).sum()
    df_debouches_par_bisemaine = df_debouches_par_semaine.rolling(
        2, step=2).mean()
    df_debouches_par_bisemaine[config["debouche"]["demi"]] *= 2
    
    # Remplissage de la première semaine avec la troisième
    df_debouches_par_bisemaine.iloc[0] = df_debouches_par_bisemaine.iloc[2]

    # Calcul des poids (sommant à 1) du chiffre d'affaire mensuel total
    dates = pd.to_datetime(
        df_debouches_par_bisemaine.index.get_level_values(
            'year').astype(str) + '-W' +
        df_debouches_par_bisemaine.index.get_level_values(
            'week').astype(str).str.zfill(2) + '-1', format='%G-W%V-%u')
    df_tmp = df_debouches_par_bisemaine.copy()
    df_tmp.index = dates
    df_tmp.index.name = "Mois"
    df_poids_debouches = df_tmp.groupby(df_tmp.index.month).sum()
    df_poids_debouches[config["debouche"]["demi"]] /= 2
    df_poids_debouches /= df_poids_debouches.sum()
    s_poids_total = df_poids_debouches.mean("columns")
    s_poids_total.name = "Poids"

    # Calcul du chiffre par année
    i_annees = [int(annee) for annee in config["source"]["annees"]]
    df_debouches_annuel = df_debouches_par_bisemaine.groupby(
        'year').sum().loc[i_annees] * 2
    df_debouches_annuel[config["debouche"]["demi"]] /= 2
    colonnes = ["AMAP", "Professionnels"]
    df_debouches_annuel.loc[:, colonnes] = df[[
        config["source"]["colonne_amap"],
        config["source"]["colonne_pro"]]].groupby(
            df.index.year).sum().set_axis(colonnes, axis="columns")
    df_debouches_annuel.index.name = "Année"

    # Sauvegarde
    chemin_bisemaine = Path(config["destination"]["chemin"])
    chemin_bisemaine = chemin_bisemaine.with_stem(
        chemin_bisemaine.stem + "_bisemaine")
    chemin_bisemaine.parent.mkdir(parents=True, exist_ok=True)
    df_debouches_par_bisemaine.to_csv(chemin_bisemaine)

    chemin_poids = Path(config["destination"]["chemin"])
    chemin_poids = chemin_poids.with_stem(
        chemin_poids.stem + "_poids")
    s_poids_total.to_csv(chemin_poids)

    chemin_annuel = Path(config["destination"]["chemin"])
    chemin_annuel = chemin_annuel.with_stem(
        chemin_annuel.stem + "_annuel")
    df_debouches_annuel.to_csv(chemin_annuel)

    # Lecture tableur d'organisation du travail
    chemin_organisation_travail = Path(
        config["organisation_travail"]["dossier"],
        config["organisation_travail"]["fichier"]
    )
    df_orga = pd.read_excel(
        chemin_organisation_travail,
        sheet_name=config["organisation_travail"]["feuille"],
        header=0, index_col=0, nrows=7)
    s_cout = df_orga[config["organisation_travail"]["colonne_cout"]]

    # Figures
    # CA sur 2 semaines par débouché
    figsize = plt.rcParams['figure.figsize']
    figsize[0] = figsize[0] * config["image"]["figxscale"]
    fig, ax = plt.subplots(figsize=figsize)
    for annee in config["source"]["annees"]: 
        df_debouches_par_bisemaine.loc[int(annee)].plot(
            ax=ax, color=COLORS,
            linestyle=config["image"]["linestyles"][annee],
            linewidth=config["image"]["linewidth"], legend=False)
    ax.set_xlabel("Semaine de l'année")
    ax.set_ylabel("CA sur 2 semaines par débouché (€)")
    ylim = (0, df_debouches_par_bisemaine.max().max() * 1.05)
    ax.set_ylim(ylim)
    box = ax.get_position()
    ax.set_position([
        box.x0,
        box.y0,
        box.width / config["image"]["figxscale"],
        box.height
    ])
    debouches = df_debouches_par_bisemaine.columns
    debouche_handles = [
        Line2D(
            [0], [0], color=color, lw=config["image"]["linewidth"],
            label=col
        )
        for col, color in zip(debouches, COLORS)
    ]
    legend_debouches = ax.legend(
        handles=debouche_handles,
        title="Débouché",
        loc="upper left",
        bbox_to_anchor=(1, 1)
    )
    annee_handles = [
        Line2D(
            [0], [0], color="k", lw=config["image"]["linewidth"],
            label=annee, linestyle=config["image"]["linestyles"][annee]
        )
        for annee in config["source"]["annees"]
    ]
    legend_annees = ax.legend(
        handles=annee_handles,
        title="Année",
        loc="lower left",
        bbox_to_anchor=(1, 0.15)
    )
    ax.add_artist(legend_debouches)
    ax.grid(True)
    sannees = "_".join(config["source"]["annees"])
    fig_chemin = Path(config["image"]["fig_dossier"],
                      f'ca_par_debouche_{sannees}.png')
    fig_chemin.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_chemin, **config["image"]["savefig_kwargs"])

    # CA sur l'année par débouché
    fig, ax = plt.subplots()
    df_debouches_annuel_ke = df_debouches_annuel / 1000
    df_debouches_annuel_ke.T.plot(ax=ax, kind='bar')
    ax.set_ylabel("CA sur l'année par débouché (k€)")
    ylim_annuel = (0, df_debouches_annuel_ke.max().max() * 1.05)
    ax.set_ylim(ylim_annuel)
    plt.xticks(rotation=45)
    plt.tight_layout()
    ax.grid(True)
    fig_chemin = Path(config["image"]["fig_dossier"],
                      f'ca_annuel_par_debouche_{sannees}.png')
    fig.savefig(fig_chemin, **config["image"]["savefig_kwargs"])

    # Figure saison pour chaque débouché
    for k, (debouche, df_deb) in enumerate(
            df_debouches_par_bisemaine.items()):
        fig, ax = plt.subplots()
        moy = df_deb.groupby('week').mean()
        cout = s_cout.loc[debouche] * 2
        for annee in config["source"]["annees"]: 
            df_deb.loc[int(annee)].plot(
                ax=ax, color=COLORS[k],
                linestyle=config["image"]["linestyles"][annee],
                linewidth=config["image"]["linewidth"], label=annee)
        xlim = ax.get_xlim()
        moy.plot(ax=ax, color=COLORS[k], linestyle='-',
                 linewidth=1, label='Moyenne')
        ax.hlines([cout], *xlim, color='k', linestyle='-', linewidth=1,
                  label=config["organisation_travail"]["colonne_cout"])
        ax.set_ylim(ylim)
        ax.set_xlabel("Semaine de l'année")
        ax.set_ylabel(f"CA sur 2 semaines - {debouche} (€)")
        ax.grid(True)
        ax.legend()
        fig_chemin = Path(config["image"]["fig_dossier"],
                          f"ca_{debouche}_{sannees}.png")
        fig.savefig(fig_chemin, **config["image"]["savefig_kwargs"])

    # Figure saison débouchés aggrégés
    df_deb = df_debouches_par_bisemaine.sum("columns")
    fig, ax = plt.subplots()
    moy = df_deb.groupby('week').mean()
    for annee in config["source"]["annees"]: 
        df_deb.loc[int(annee)].plot(
            ax=ax, color=COLORS[k],
            linestyle=config["image"]["linestyles"][annee],
            linewidth=config["image"]["linewidth"], label=annee)
    xlim = ax.get_xlim()
    moy.plot(ax=ax, color=COLORS[k], linestyle='-',
             linewidth=1, label='Moyenne')
    ax.set_xlabel("Semaine de l'année")
    ax.set_ylabel(f"CA sur 2 semaines - total (€)")
    ax.grid(True)
    ax.legend()
    fig_chemin = Path(config["image"]["fig_dossier"],
                      f"ca_total_{sannees}.png")
    fig.savefig(fig_chemin, **config["image"]["savefig_kwargs"])

    plt.show(block=False)
        
def load_config():
    with open(CHEMIN_CONFIG, "rb") as f:
        config = tomllib.load(f)

    return config

if __name__ == "__main__":
    main()
